import asyncio
import gzip
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from functools import cached_property
from multiprocessing.pool import ThreadPool
from time import sleep
from typing import (
    Callable,
    ClassVar,
    Dict,
    Generator,
    Iterable,
    Iterator,
    List,
    Optional, AsyncGenerator,
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

_default_header = {"user-agent": "Fundus"}


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
class URLSource(Iterable[str], ABC):
    url: str
    url_filter: UrlFilter = lambda url: not bool(url)

    _request_header: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self._request_header:
            self._request_header = _default_header

    def set_header(self, request_header: Dict[str, str]) -> None:
        self._request_header = request_header

    @abstractmethod
    def _get_pre_filtered_urls(self) -> Iterator[str]:
        pass

    def __iter__(self) -> Iterator[str]:
        yield from filter(inverse(self.url_filter), self._get_pre_filtered_urls())


@dataclass
class RSSFeed(URLSource):
    def _get_pre_filtered_urls(self) -> Iterator[str]:
        with requests.Session() as session:
            content = session.get(self.url, headers=self._request_header).content
            rss_feed = feedparser.parse(content)
            if exception := rss_feed.get("bozo_exception"):
                basic_logger.warning(f"Warning! Couldn't parse rss feed at {self.url}. Exception: {exception}")
                return iter(())
            else:
                return (entry["link"] for entry in rss_feed["entries"])


@dataclass
class Sitemap(URLSource):
    recursive: bool = True
    reverse: bool = False
    sitemap_filter: UrlFilter = lambda url: not bool(url)

    _decompressor: ClassVar[_ArchiveDecompressor] = _ArchiveDecompressor()
    _sitemap_selector: ClassVar[XPath] = CSSSelector("sitemap > loc")
    _url_selector: ClassVar[XPath] = CSSSelector("url > loc")

    def _get_pre_filtered_urls(self) -> Iterator[str]:
        def yield_recursive(url: str):
            try:
                response = session.get(url=url, headers=self._request_header)
                response.raise_for_status()
            except (HTTPError, ConnectionError) as error:
                basic_logger.warning(f"Warning! Couldn't reach sitemap {url} so skipped it. Exception: {error}")
                return
            content = response.content
            if (content_type := response.headers.get("Content-Type")) in self._decompressor.supported_file_formats:
                content = self._decompressor.decompress(content, content_type)
            tree = lxml.html.fromstring(content)
            urls = [node.text_content() for node in self._url_selector(tree)]
            yield from reversed(urls) if self.reverse else urls
            if self.recursive:
                sitemap_locs = [node.text_content() for node in self._sitemap_selector(tree)]
                filtered_locs = list(filter(inverse(self.sitemap_filter), sitemap_locs))
                for loc in reversed(filtered_locs) if self.reverse else filtered_locs:
                    yield from yield_recursive(loc)

        with requests.Session() as session:
            yield from yield_recursive(self.url)


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
        url_source: Iterable[str],
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

    async def async_fetch(self, delay: Optional[Callable[[], float]] = None) -> AsyncGenerator[ArticleSource, None]:
        async with aiohttp.ClientSession(headers=self.request_header) as session:
            url_iterator = filter(inverse(self.url_filter), self.url_source)
            last_request_time = time.time()
            for url in url_iterator:
                async with session.get(url) as response:
                    if delay and (actual_delay := delay() - time.time() + last_request_time) > 0:
                        basic_logger.debug(f"Sleep for {actual_delay} seconds.")
                        await asyncio.sleep(actual_delay)
                    try:
                        html = await response.text()
                        last_request_time = time.time()
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
