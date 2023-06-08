import gzip
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
    Optional,
)

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
        delay: Optional[Callable[[], float]] = None,
        request_header: Optional[Dict[str, str]] = None,
    ):
        self.url_source = url_source
        self.publisher = publisher
        self.url_filter = url_filter or (lambda url: not bool(url))
        self.max_threads = max_threads
        self.delay = delay
        self.request_header = request_header or _default_header
        if isinstance(url_source, URLSource):
            url_source.set_header(self.request_header)

    def _batched_fetch(self) -> Generator[List[Optional[ArticleSource]], int, None]:
        with requests.Session() as session:

            def thread(url: str) -> Optional[ArticleSource]:
                if self.delay:
                    sleep(self.delay())
                try:
                    response = session.get(url=url, headers=self.request_header)
                    response.raise_for_status()
                except HTTPError as error:
                    basic_logger.warn(f"Skipped {url} because of {error}")
                    return None
                except requests.exceptions.TooManyRedirects as error:
                    basic_logger.info(f"Skipped {url} because of {error}")
                    return None
                if history := response.history:
                    basic_logger.info(f"Got redirected {len(history)} time(s) from {url} -> {response.url}")

                article_source = ArticleSource(
                    url=response.url,
                    html=response.text,
                    crawl_date=datetime.now(),
                    publisher=self.publisher,
                    source=self,
                )
                return article_source

            with ThreadPool(processes=self.max_threads) as pool:
                url_iterator = filter(inverse(self.url_filter), self.url_source)
                empty = False
                while not empty:
                    current_size = batch_size = yield  # type: ignore
                    batch_urls = []
                    while current_size > 0 and (nxt := next(url_iterator, None)):
                        batch_urls.append(nxt)
                        current_size -= 1
                    if not batch_urls:
                        break
                    elif len(batch_urls) < batch_size:
                        empty = True
                    yield pool.map(thread, batch_urls)

    def fetch(self, batch_size: int = 10) -> Iterator[ArticleSource]:
        gen = self._batched_fetch()
        while True:
            try:
                next(gen)
                yield from filter(lambda x: bool(x), gen.send(batch_size))
            except StopIteration:
                break
