import gzip
import itertools
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from functools import cached_property
from typing import Callable, ClassVar, Dict, Iterable, Iterator, List, Optional

import feedparser
import lxml.html
import validators
from lxml.cssselect import CSSSelector
from lxml.etree import XPath
from requests import ConnectionError, HTTPError

from fundus.logging import create_logger
from fundus.scraping.filter import URLFilter, inverse
from fundus.scraping.session import _default_header, session_handler

logger = create_logger(__name__)


class _ArchiveDecompressor:
    def __init__(self):
        self.archive_mapping: Dict[str, Callable[[bytes], bytes]] = {
            "application/x-gzip": self._decompress_gzip,
            "gzip": self._decompress_gzip,
        }

    @staticmethod
    def _decompress_gzip(compressed_content: bytes) -> bytes:
        decompressed_content = gzip.decompress(compressed_content)
        return decompressed_content

    def decompress(self, content: bytes, file_format: "str") -> bytes:
        decompress_function = self.archive_mapping[file_format]
        return decompress_function(content)

    @cached_property
    def supported_file_formats(self) -> List[str]:
        return list(self.archive_mapping.keys())


@dataclass
class URLSource(Iterable[str], ABC):
    url: str

    _request_header: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self._request_header:
            self._request_header = _default_header
        if not validators.url(self.url, strict_query=False):
            logger.error(f"{type(self).__name__} initialized with invalid URL {self.url}")

    def set_header(self, request_header: Dict[str, str]) -> None:
        self._request_header = request_header

    @abstractmethod
    def __iter__(self) -> Iterator[str]:
        raise NotImplemented

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
    def __iter__(self) -> Iterator[str]:
        session = session_handler.get_session()
        try:
            response = session.get(self.url, headers=self._request_header)
        except (HTTPError, ConnectionError) as err:
            logger.warning(f"Warning! Couldn't parse rss feed {self.url!r} because of {err}")
            return
        html = response.text
        rss_feed = feedparser.parse(html)
        if exception := rss_feed.get("bozo_exception"):
            logger.warning(f"Warning! Couldn't parse rss feed {self.url!r} because of {exception}")
            return
        else:
            yield from filter(bool, (entry.get("link") for entry in rss_feed["entries"]))


@dataclass
class Sitemap(URLSource):
    recursive: bool = True
    reverse: bool = False
    sitemap_filter: URLFilter = lambda url: not bool(url)

    _decompressor: ClassVar[_ArchiveDecompressor] = _ArchiveDecompressor()
    _sitemap_selector: ClassVar[XPath] = CSSSelector("sitemap > loc")
    _url_selector: ClassVar[XPath] = CSSSelector("url > loc")

    def __iter__(self) -> Iterator[str]:
        def yield_recursive(sitemap_url: str) -> Iterator[str]:
            session = session_handler.get_session()
            if not validators.url(sitemap_url):
                logger.info(f"Skipped sitemap {sitemap_url!r} because the URL is malformed")
            try:
                response = session.get(url=sitemap_url, headers=self._request_header)
            except (HTTPError, ConnectionError) as error:
                logger.warning(f"Warning! Couldn't reach sitemap {sitemap_url!r} because of {error!r}")
                return
            content = response.content
            if (content_type := response.headers.get("content-type")) in self._decompressor.supported_file_formats:
                content = self._decompressor.decompress(content, content_type)
            if not content:
                logger.warning(f"Warning! Empty sitemap at {sitemap_url!r}")
                return
            tree = lxml.html.fromstring(content)
            urls = [node.text_content() for node in self._url_selector(tree)]
            if urls:
                for new_url in reversed(urls) if self.reverse else urls:
                    yield new_url
            elif self.recursive:
                sitemap_locs = [node.text_content() for node in self._sitemap_selector(tree)]
                filtered_locs = list(filter(inverse(self.sitemap_filter), sitemap_locs))
                for loc in reversed(filtered_locs) if self.reverse else filtered_locs:
                    yield from yield_recursive(loc)

        yield from yield_recursive(self.url)


@dataclass
class NewsMap(Sitemap):
    pass
