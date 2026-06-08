import bz2
import gzip
import itertools
import lzma
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
    Pattern,
    Set,
    Tuple,
)
from urllib.parse import unquote, urljoin, urlparse

import feedparser
from curl_cffi.requests.exceptions import ConnectionError, HTTPError, ReadTimeout
from lxml.etree import XMLParser, XPath, fromstring

from fundus.logging import create_logger
from fundus.scraping.filter import URLFilter, inverse
from fundus.scraping.session import InterruptableSession, _default_header, session_handler

logger = create_logger(__name__)


def is_valid_url(url: str) -> bool:
    """True if the URL has an http/https scheme and a non-empty network location."""
    parsed = urlparse(url)
    return bool(parsed.scheme in ("http", "https") and parsed.netloc)


def strip_query_and_fragment(url: str) -> str:
    """Return the URL with its query string and fragment removed.

    Intended for *identity* use (dedup keys, equality probes), not for fetching:
    the result may resolve to a different resource than the input on servers that
    rely on query parameters for routing.
    """
    if any(indicator in url for indicator in ("?", "#")):
        return urljoin(url, urlparse(url).path)
    return url


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

        except (HTTPError, ConnectionError, ReadTimeout) as err:
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
        sort_predicate (Optional[Pattern[str]]): If set, sub-sitemap URLs are sorted (descending)
            by the matched substring of this pattern; the pattern must match every URL.
    """

    recursive: bool = True
    reverse: bool = False
    sitemap_filter: URLFilter = _default_sitemap_filter
    sort_predicate: Optional[Pattern[str]] = None

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
        except (HTTPError, ConnectionError, ReadTimeout) as error:
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
        """Extract sub-sitemap <loc> values, sorted by sort_predicate and filtered."""
        locs = [node.text for node in self._sitemap_selector(tree)]

        if self.sort_predicate is not None:
            pattern = self.sort_predicate

            def key(text: str) -> str:
                if match := pattern.search(text):
                    return match.group()
                raise NotImplementedError("<sort_predicate> must match in all sitemap URLs")

            locs = sorted(locs, key=key, reverse=True)

        return list(filter(inverse(self.sitemap_filter), locs))

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
    news sitemaps over full archive sitemaps via __SOURCE_ORDER__ in base_objects.py.
    """
