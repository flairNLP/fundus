import asyncio
import gzip
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from functools import cached_property
from typing import (
    AsyncIterable,
    AsyncIterator,
    Callable,
    ClassVar,
    Dict,
    Iterable,
    List,
    Optional,
)

import aiohttp
import feedparser
import lxml.html
import requests
from lxml.cssselect import CSSSelector
from lxml.etree import XPath
from requests import HTTPError

from fundus.logging.logger import basic_logger
from fundus.scraping.filter import UrlFilter, inverse
from fundus.utils.more_async import make_async

_default_header = {"user-agent": "Fundus"}
_connector = aiohttp.TCPConnector(limit=50)
async_session = aiohttp.ClientSession(connector=_connector)


class _ArchiveDecompressor:
    def __init__(self):
        self.archive_mapping: Dict[str, Callable[[bytes], bytes]] = {"application/x-gzip": self._decompress_gzip}

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
class StaticSource(AsyncIterable[str]):
    links: Iterable[str]

    async def __aiter__(self) -> AsyncIterator[str]:
        async for url in make_async(self.links):
            yield url


@dataclass
class URLSource(AsyncIterable[str], ABC):
    url: str
    url_filter: UrlFilter = lambda url: not bool(url)

    _request_header: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self._request_header:
            self._request_header = _default_header

    def set_header(self, request_header: Dict[str, str]) -> None:
        self._request_header = request_header

    @abstractmethod
    def _get_pre_filtered_urls(self) -> AsyncIterator[str]:
        pass

    async def __aiter__(self) -> AsyncIterator[str]:
        async for url in self._get_pre_filtered_urls():
            # noinspection PyArgumentList
            if url and self.url_filter(url):
                continue
            else:
                yield url


@dataclass
class RSSFeed(URLSource):
    async def _get_pre_filtered_urls(self) -> AsyncIterator[str]:
        async with async_session.get(self.url, headers=self._request_header) as response:
            html = await response.text()
            rss_feed = feedparser.parse(html)
            if exception := rss_feed.get("bozo_exception"):
                basic_logger.warning(f"Warning! Couldn't parse rss feed at {self.url}. Exception: {exception}")
                return
            else:
                for url in (entry["link"] for entry in rss_feed["entries"]):
                    yield url


@dataclass
class Sitemap(URLSource):
    recursive: bool = True
    reverse: bool = False
    sitemap_filter: UrlFilter = lambda url: not bool(url)

    _decompressor: ClassVar[_ArchiveDecompressor] = _ArchiveDecompressor()
    _sitemap_selector: ClassVar[XPath] = CSSSelector("sitemap > loc")
    _url_selector: ClassVar[XPath] = CSSSelector("url > loc")

    async def _get_pre_filtered_urls(self) -> AsyncIterator[str]:
        async def yield_recursive(link: str) -> AsyncIterator[str]:
            async with async_session.get(url=link, headers=self._request_header) as response:
                try:
                    response.raise_for_status()
                except (HTTPError, ConnectionError) as error:
                    basic_logger.warning(f"Warning! Couldn't reach sitemap {link} so skipped it. Exception: {error}")
                    return
                content = await response.content.read()
                if (content_type := response.headers.get("Content-Type")) in self._decompressor.supported_file_formats:
                    content = self._decompressor.decompress(content, content_type)
                tree = lxml.html.fromstring(content)
                urls = [node.text_content() for node in self._url_selector(tree)]
                for new_link in reversed(urls) if self.reverse else urls:
                    yield new_link
                if self.recursive:
                    sitemap_locs = [node.text_content() for node in self._sitemap_selector(tree)]
                    filtered_locs = list(filter(inverse(self.sitemap_filter), sitemap_locs))
                    for loc in reversed(filtered_locs) if self.reverse else filtered_locs:
                        async for new_link in yield_recursive(loc):
                            yield new_link

        async for url in yield_recursive(self.url):
            yield url


@dataclass
class NewsMap(Sitemap):
    pass


@dataclass(frozen=True)
class ArticleSource:
    url: str
    html: str
    crawl_date: datetime
    publisher: Optional[str] = None
    source: Optional["Source"] = None


class Source:
    def __init__(
        self,
        url_source: AsyncIterable[str],
        publisher: Optional[str],
        url_filter: Optional[UrlFilter] = None,
        max_threads: int = 10,
        request_header: Optional[Dict[str, str]] = None,
    ):
        self.url_source = url_source
        self.publisher = publisher
        self.url_filter = url_filter or (lambda url: not bool(url))
        self.max_threads = max_threads
        self.request_header = request_header or _default_header
        if isinstance(url_source, URLSource):
            url_source.set_header(self.request_header)

    async def async_fetch(self, delay: Optional[Callable[[], float]] = None) -> AsyncIterator[ArticleSource]:
        async for url in self.url_source:
            last_request_time = time.time()
            async with async_session.get(url, headers=self.request_header) as response:
                if delay and (actual_delay := delay() - time.time() + last_request_time) > 0:
                    basic_logger.debug(f"Sleep for {actual_delay} seconds.")
                    await asyncio.sleep(actual_delay)
                try:
                    html = await response.text()
                    response.raise_for_status()
                except HTTPError as error:
                    basic_logger.warn(f"Skipped {url} because of {error}")
                    return
                except requests.exceptions.TooManyRedirects as error:
                    basic_logger.info(f"Skipped {url} because of {error}")
                    return
                if history := response.history:
                    basic_logger.info(f"Got redirected {len(history)} time(s) from {url} -> {response.url}")
                yield ArticleSource(
                    url=str(response.url),
                    html=html,
                    crawl_date=datetime.now(),
                    publisher=self.publisher,
                    source=self,
                )
