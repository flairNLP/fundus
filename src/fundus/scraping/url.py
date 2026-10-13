import bz2
import gzip
import itertools
import lzma
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterable,
    Iterator,
    List,
    NamedTuple,
    Optional,
    Set,
    Tuple,
    Type,
)
from urllib.parse import unquote

import feedparser
from curl_cffi.requests.exceptions import ConnectionError, HTTPError, Timeout
from lxml.etree import XMLParser, XPath, fromstring

from fundus.logging import create_logger
from fundus.scraping.filter import URLFilter, inverse
from fundus.scraping.session import InterruptableSession, _default_header, session_handler
from fundus.utils.iteration import iterate_all_subclasses
from fundus.utils.url import is_valid_url

logger = create_logger(__name__)


@dataclass
class URLSource(Iterable[str], ABC):
    """Abstract source of article URLs for a single feed/sitemap endpoint.

    Concrete subclasses (RSSFeed, Sitemap, NewsMap) implement fetch() to stream URLs from
    the endpoint at <url>. Iterating the source directly (__iter__) uses a default session
    and headers for standalone use; production scraping calls fetch() through WebSource with
    publisher-specific session and headers.

    Attributes:
        url (str): The feed/sitemap URL to pull article URLs from.
        languages (Set[str]): Language codes the source is known to serve, if any.
    """

    url: str
    languages: Set[str] = field(default_factory=set)
    interleave: bool = False

    def __post_init__(self):
        """Warn (but don't fail) if the configured URL is malformed."""
        if not is_valid_url(self.url):
            logger.error(f"{type(self).__name__} initialized with invalid URL {self.url}")

    @abstractmethod
    def fetch(self, session: InterruptableSession, headers: Dict[str, str]) -> Iterator[str]:
        """Fetch URLs using the provided session and headers.

        Args:
            session: The HTTP session to use for requests.
            headers: Request headers to include. Note that when the session was created
                with an impersonate profile, headers may be dropped in favour of the
                browser fingerprint (see InterruptableSession.get_with_interrupt).
        """
        raise NotImplementedError

    def __iter__(self) -> Iterator[str]:
        """Iterate URLs using a default session and headers.

        Intended for standalone/testing use. Production scraping goes through
        WebSource, which calls fetch() with publisher-specific session and headers.
        """
        return self.fetch(session_handler.get_session(), _default_header)

    def get_urls(self, max_urls: Optional[int] = None) -> Iterator[str]:
        """Returns a generator yielding up to <max_urls> URLs from <self>.


        Args:
            max_urls (int): Number of max URLs to return. Set value is
                an upper bound and not necessarily the actual number of
                URLs. If set to None, the source will be exhausted until
                StopIteration is hit. Defaults to None.

        Yields:
            str: The next URL.
        """
        return itertools.islice(self, max_urls)


@dataclass
class RSSFeed(URLSource):
    """URLSource that yields article links from an RSS/Atom feed."""

    def fetch(self, session: InterruptableSession, headers: Dict[str, str]) -> Iterator[str]:
        try:
            response = session.get_with_interrupt(self.url, headers=headers)

        except (HTTPError, ConnectionError, Timeout) as err:
            logger.warning(f"Warning! Couldn't parse rss feed {self.url!r} because of {err}")
            return
        except Exception as error:
            logger.error(f"Warning! Couldn't parse rss feed {self.url!r} because of an unexpected error {error!r}")
            return

        html = response.text
        rss_feed = feedparser.parse(html)
        if exception := rss_feed.get("bozo_exception"):
            logger.warning(f"Warning! Couldn't parse rss feed {self.url!r} because of {exception}")
            return
        else:
            urls = filter(bool, (entry.get("link") for entry in rss_feed["entries"]))
            for url in urls:
                # Some publishers emit URLs with percent-encoded path separators
                # (e.g. `https://example.com%2Farticle.html`); see PR #753.
                yield unquote(url)


class _Codec(NamedTuple):
    """A supported compression format: its name, leading magic bytes, and decompress function."""

    name: str
    magic: bytes
    decompress: Callable[[bytes], bytes]


# Identified by magic-byte sniff rather than headers: the formats we support all carry
# unambiguous signatures, and sniffing handles misadvertised or header-less payloads alike.
_CODECS: Tuple[_Codec, ...] = (
    _Codec("gzip", b"\x1f\x8b", gzip.decompress),
    _Codec("bzip2", b"BZh", bz2.decompress),
    _Codec("xz", b"\xfd7zXZ\x00", lzma.decompress),
)


def decompress(content: bytes) -> bytes:
    """Decompress content if its leading bytes match a known codec, else return unchanged."""
    for codec in _CODECS:
        if content.startswith(codec.magic):
            return codec.decompress(content)
    return content


def _default_sitemap_filter(url: str) -> bool:
    """Default sitemap_filter: drop empty/falsy entries, keep everything else."""
    return not bool(url)


def numeric_sort_key(pattern: str, reverse: bool = False) -> Callable[[str], Tuple[int, ...]]:
    """Build a <sort_key> ordering sitemaps by the integer capture groups of <pattern>.

    Groups are compared numerically rather than as text, so unpadded indices order as
    1, 2, ..., 10 instead of 1, 10, 2. Pass reverse=True to negate them, putting the
    highest value first - use it when the number grows with recency (e.g. a date),
    and leave it off when it grows with age (e.g. a sitemap chunk counted from newest).

    Raises ValueError for a URL the pattern doesn't match; <sitemap_filter> is applied
    first, so the key only ever sees the sitemaps that were kept.
    """
    compiled = re.compile(pattern)
    sign = -1 if reverse else 1

    def key(url: str) -> Tuple[int, ...]:
        if match := compiled.search(url):
            return tuple(sign * int(group) for group in match.groups())
        raise ValueError(f"<sort_key> pattern {pattern!r} does not match sitemap URL {url!r}")

    return key


@dataclass
class Sitemap(URLSource):
    """URLSource that yields article links from an XML sitemap, descending into sitemap indexes.

    Attributes:
        recursive (bool): If True, follow nested <sitemap> references in a sitemap index.
            Defaults to True.
        reverse (bool): If True, yield URLs (and descend into sub-sitemaps) in reverse order.
            Defaults to False.
        sitemap_filter (URLFilter): Filter applied to sub-sitemap <loc> values; a truthy result
            drops the entry. Defaults to dropping only empty values.
        sort_key (Optional[Callable[[str], Any]]): If set, the sub-sitemap URLs kept by
            <sitemap_filter> are sorted (ascending) by this key; see numeric_sort_key.
    """

    recursive: bool = True
    reverse: bool = False
    sitemap_filter: URLFilter = _default_sitemap_filter
    sort_key: Optional[Callable[[str], Any]] = None

    _sitemap_selector: ClassVar[XPath] = XPath("//*[local-name()='sitemap']/*[local-name()='loc']")
    _url_selector: ClassVar[XPath] = XPath("//*[local-name()='url']/*[local-name()='loc']")

    @staticmethod
    def _fetch_bytes(
        sitemap_url: str,
        session: InterruptableSession,
        headers: Dict[str, str],
    ) -> Optional[bytes]:
        """Fetch sitemap bytes, decompressing if needed. Returns None on any failure.

        Handles HTTP errors, decompression failures, and empty bodies. Each failure
        mode is logged at its point of occurrence; callers just check for None.
        """
        if not is_valid_url(sitemap_url):
            logger.info(f"Skipped sitemap {sitemap_url!r} because the URL is malformed")
            return None
        try:
            response = session.get_with_interrupt(url=sitemap_url, headers=headers)
        except (HTTPError, ConnectionError, Timeout) as error:
            logger.warning(f"Warning! Couldn't reach sitemap {sitemap_url!r} because of {error!r}")
            return None
        except Exception as error:
            logger.error(f"Warning! Couldn't reach sitemap {sitemap_url!r} because of an unexpected error {error!r}")
            return None

        content = response.content.strip()
        try:
            content = decompress(content)
        except Exception as error:
            logger.warning(f"Decompression failed for {sitemap_url!r}: {error!r}")
            return None
        if not content:
            logger.warning(f"Warning! Empty sitemap at {sitemap_url!r}")
            return None
        return content

    def _ordered_sub_locs(self, tree: Any) -> List[str]:
        """Extract sub-sitemap <loc> values, filtered by sitemap_filter and then sorted by sort_key."""
        locs = [node.text for node in self._sitemap_selector(tree)]
        locs = list(filter(inverse(self.sitemap_filter), locs))

        if self.sort_key is not None:
            locs.sort(key=self.sort_key)

        return locs

    def _yield_from_sitemap(
        self,
        sitemap_url: str,
        session: InterruptableSession,
        headers: Dict[str, str],
        parser: XMLParser,
    ) -> Iterator[str]:
        # Download (and decompress) the sitemap bytes.
        content = self._fetch_bytes(sitemap_url, session, headers)
        if content is None:
            return

        # Parse the bytes into an XML tree.
        tree = fromstring(content, parser=parser)
        if tree is None:
            logger.warning(f"Warning! Couldn't parse sitemap {sitemap_url!r}")  # type: ignore[unreachable]
            return

        # Yield the article URLs contained in this sitemap, if any.
        urls = [node.text for node in self._url_selector(tree)]
        if urls:
            for new_url in reversed(urls) if self.reverse else urls:
                yield unquote(new_url)
            return

        # Otherwise descend into nested sitemap-index references.
        if not self.recursive:
            return
        locs = self._ordered_sub_locs(tree)
        for loc in reversed(locs) if self.reverse else locs:
            yield from self._yield_from_sitemap(loc, session, headers, parser)

    def fetch(self, session: InterruptableSession, headers: Dict[str, str]) -> Iterator[str]:
        # lxml parsers serialize access across threads; construct one per fetch() so
        # concurrent sitemap fetches don't contend. Each fetch() generator is consumed
        # by a single thread, so the parser stays single-threaded for its lifetime.
        parser = XMLParser(strip_cdata=False, recover=True)
        yield from self._yield_from_sitemap(self.url, session, headers, parser)


@dataclass
class NewsMap(Sitemap):
    """Marker subclass for Google-News-style sitemaps (recent articles only).

    Parsing is identical to Sitemap; the distinct type lets the scraper prioritize
    news sitemaps over full archive sitemaps via SourceHandler.__SOURCE_ORDER__.
    """


class SourceHandler(Iterable[URLSource]):
    """The sources of a publisher, in crawl order and grouped into execution batches.

    Sources are ordered by their type following <__SOURCE_ORDER__>, and within a type by
    the order they were declared in. Sources marked with <URLSource.interleave> are grouped
    with the other interleaved sources of their type into a single batch, which the scraper
    round-robins rather than exhausting one source after another.
    """

    __SOURCE_ORDER__: ClassVar[Tuple[Type[URLSource], ...]] = (RSSFeed, NewsMap, Sitemap)

    def __init__(self, sources: Iterable[URLSource]) -> None:
        collected = tuple(sources)

        for source in collected:
            if not isinstance(source, URLSource):
                raise TypeError(
                    f"Unexpected type {type(source).__name__!r} as source. "
                    f"Allowed are {', '.join(repr(cls.__name__) for cls in iterate_all_subclasses(URLSource))}"
                )

        self._sources: Tuple[URLSource, ...] = tuple(sorted(collected, key=self._rank))

    @classmethod
    def _rank(cls, source: URLSource) -> int:
        """The position of <source>'s type in the crawl order.

        Types not listed in <__SOURCE_ORDER__> are processed last rather than raising, so that
        URLSource implementations living outside this module stay usable without registration.
        Since sorting is stable, they keep their declared order among themselves.
        """
        source_type = type(source)
        if source_type in cls.__SOURCE_ORDER__:
            return cls.__SOURCE_ORDER__.index(source_type)
        return len(cls.__SOURCE_ORDER__)

    def __iter__(self) -> Iterator[URLSource]:
        return iter(self._sources)

    def __len__(self) -> int:
        return len(self._sources)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, SourceHandler):
            return NotImplemented
        return self._sources == other._sources

    def __repr__(self) -> str:
        return f"{type(self).__name__}({list(self._sources)!r})"

    def batches(self) -> Iterator[Tuple[URLSource, ...]]:
        """Yields the sources as units of work, in crawl order.

        A batch holding more than one source is meant to be round-robined. Interleaved sources
        of the same type share a batch, which takes the position of the first of them; every
        other source forms a batch of its own.

        Yields:
            Tuple[URLSource, ...]: The next batch of sources.
        """
        # maps a source type onto the batch collecting its interleaved sources. Since sources
        # are sorted by type, at most one such batch is open at any time, but keying by type
        # keeps this independent of that guarantee.
        interleaved: Dict[Type[URLSource], List[URLSource]] = {}
        batches: List[List[URLSource]] = []

        for source in self._sources:
            if not source.interleave:
                batches.append([source])
            elif (open_batch := interleaved.get(type(source))) is not None:
                open_batch.append(source)
            else:
                # placed at the position of the first interleaved source of this type
                interleaved[type(source)] = new_batch = [source]
                batches.append(new_batch)

        for batch in batches:
            yield tuple(batch)

    def filter(
        self,
        source_types: Optional[Iterable[Type[URLSource]]] = None,
        languages: Optional[Iterable[str]] = None,
    ) -> "SourceHandler":
        """Returns a new handler holding only the sources matching the given restrictions.

        An empty or omitted argument does not restrict on that axis. Filtering an already
        filtered handler narrows it further, so chained calls intersect.

        Args:
            source_types (Optional[Iterable[Type[URLSource]]]): Only keep sources of these types.
            languages (Optional[Iterable[str]]): Only keep sources covering at least one of
                these languages.

        Returns:
            SourceHandler: A new handler over the surviving sources.
        """
        allowed_types = set(source_types) if source_types else set()
        allowed_languages = set(languages) if languages else set()

        return SourceHandler(
            source
            for source in self._sources
            if (not allowed_types or type(source) in allowed_types)
            and (not allowed_languages or source.languages & allowed_languages)
        )

    @property
    def languages(self) -> Set[str]:
        # deliberately not cached: PublisherGroup fills in a default language by mutating
        # the sources after the handler was built.
        return set().union(*(source.languages for source in self._sources)) if self._sources else set()

    @property
    def source_types(self) -> Set[Type[URLSource]]:
        return {type(source) for source in self._sources}
