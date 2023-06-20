import gzip
import re
from abc import ABC, abstractmethod
from collections import defaultdict
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
    Pattern,
)

import aiohttp
import feedparser
import lxml.html
from aiohttp.client_exceptions import ClientError
from aiohttp.http_exceptions import HttpProcessingError
from aiohttp.web_exceptions import HTTPError
from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.logging import basic_logger
from fundus.logging.context import get_current_context
from fundus.scraping.filter import URLFilter, inverse
from fundus.utils.more_async import async_next, make_iterable_async, timed

_default_header = {"user-agent": "Fundus"}


class SessionHandler:
    def __init__(self):
        self._factory = self._build_session_factory()

    @staticmethod
    async def _build_session_factory():
        _connector = aiohttp.TCPConnector(limit=50)
        async_session = aiohttp.ClientSession(connector=_connector)
        while True:
            yield async_session

    async def get_session(self) -> aiohttp.ClientSession:
        return await async_next(self._factory)

    async def close_current_session(self):
        session = await self.get_session()
        basic_logger.debug(f"Close session {session}")
        await session.close()
        self._factory = self._build_session_factory()


session_handler = SessionHandler()


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


_http_regex: Pattern[str] = re.compile(r"https?://(?:[a-zA-Z]|\d|[$-_@.&+]|[!*(),]|%[\da-fA-F][\da-fA-F])+")


def validate_url(url: str) -> bool:
    return bool(re.match(_http_regex, url))


@dataclass
class StaticSource(AsyncIterable[str]):
    links: Iterable[str]

    async def __aiter__(self) -> AsyncIterator[str]:
        async for url in make_iterable_async(self.links):
            yield url


@dataclass
class URLSource(AsyncIterable[str], ABC):
    url: str

    _request_header: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self):
        if not self._request_header:
            self._request_header = _default_header
        if not validate_url(self.url):
            raise ValueError(f"Invalid url '{self.url}'")

    def set_header(self, request_header: Dict[str, str]) -> None:
        self._request_header = request_header

    @abstractmethod
    def _get_pre_filtered_urls(self) -> AsyncIterator[str]:
        pass

    async def __aiter__(self) -> AsyncIterator[str]:
        async for url in self._get_pre_filtered_urls():
            yield url


@dataclass
class RSSFeed(URLSource):
    async def _get_pre_filtered_urls(self) -> AsyncIterator[str]:
        session = await session_handler.get_session()
        async with session.get(self.url, headers=self._request_header) as response:
            html = await response.text()
            rss_feed = feedparser.parse(html)
            if exception := rss_feed.get("bozo_exception"):
                basic_logger.warn(f"Warning! Couldn't parse rss feed '{self.url}' because of {exception}")
                return
            else:
                for url in (entry["link"] for entry in rss_feed["entries"]):
                    yield url


@dataclass
class Sitemap(URLSource):
    recursive: bool = True
    reverse: bool = False
    sitemap_filter: URLFilter = lambda url: not bool(url)

    _decompressor: ClassVar[_ArchiveDecompressor] = _ArchiveDecompressor()
    _sitemap_selector: ClassVar[XPath] = CSSSelector("sitemap > loc")
    _url_selector: ClassVar[XPath] = CSSSelector("url > loc")

    async def _get_pre_filtered_urls(self) -> AsyncIterator[str]:
        async def yield_recursive(link: str) -> AsyncIterator[str]:
            session = await session_handler.get_session()
            if not validate_url(link):
                basic_logger.info(f"Skipped sitemap '{link}' because of invalid URL")
            async with session.get(url=link, headers=self._request_header) as response:
                try:
                    response.raise_for_status()
                except (HTTPError, ClientError, HttpProcessingError) as error:
                    basic_logger.warn(f"Warning! Couldn't reach sitemap '{link}' because of {error}")
                    return
                content = await response.content.read()
                if response.content_type in self._decompressor.supported_file_formats:
                    content = self._decompressor.decompress(content, response.content_type)
                if not content:
                    basic_logger.warn(f"Warning! Empty sitemap at '{link}'")
                    return
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
class HTML:
    requested_url: str
    responded_url: str
    content: str
    crawl_date: datetime
    source: "HTMLSource"


class HTMLSource:
    def __init__(
        self,
        url_source: AsyncIterable[str],
        publisher: Optional[str],
        url_filter: Optional[URLFilter] = None,
        request_header: Optional[Dict[str, str]] = None,
    ):
        self.url_source = url_source
        self.publisher = publisher
        self.url_filter = [] if not url_filter else [url_filter]
        self.request_header = request_header or _default_header
        if isinstance(url_source, URLSource):
            url_source.set_header(self.request_header)

    def add_url_filter(self, url_filter: URLFilter):
        self.url_filter.append(url_filter)

    def _filter(self, url: str) -> bool:
        for f in self.url_filter:
            if f(url):
                return True
        return False

    async def async_fetch(self) -> AsyncIterator[HTML]:
        async for iteration_time, url in timed(self.url_source.__aiter__()):

            # log time to get url
            current_context = get_current_context()[self.publisher or url]
            if not current_context.get("timings"):
                current_context["timings"] = defaultdict(float)
            current_context["timings"]["url_source"] += iteration_time
            if not validate_url(url):
                basic_logger.debug(f"Skipped requested URL '{url}' because of invalid URL")
                continue

            if self._filter(url):
                basic_logger.debug(f"Skipped requested URL '{url}' because of URL filter")
                continue

            session = await session_handler.get_session()

            async with session.get(url, headers=self.request_header) as response:
                try:
                    html = await response.text()
                    response.raise_for_status()

                except (HTTPError, ClientError, HttpProcessingError, UnicodeError) as error:
                    basic_logger.info(f"Skipped requested URL '{url}' because of '{error}'")
                    continue

                except Exception as error:
                    basic_logger.warn(f"Warning! Skipped  requested URL '{url}' because of an unexpected error {error}")
                    continue

                if self._filter(url):
                    basic_logger.debug(f"Skipped responded URL '{url}' because of URL filter")
                    continue

                if response.history:
                    basic_logger.debug(f"Got redirected {len(response.history)} time(s) from {url} -> {response.url}")

                yield HTML(
                    requested_url=url,
                    responded_url=str(response.url),
                    content=html,
                    crawl_date=datetime.now(),
                    source=self,
                )
