import gzip
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property, lru_cache
from multiprocessing import cpu_count
from time import sleep
from typing import Callable, Dict, Generator, Iterable, Iterator, List, Optional

import feedparser
import lxml.html
import requests
import requests.adapters
from lxml.cssselect import CSSSelector
from lxml.etree import XPath
from requests import ConnectionError, HTTPError, TooManyRedirects

from fundus.logging.logger import basic_logger
from fundus.scraping.filter import UrlFilter, _not

_max_threads = cpu_count() + 4


def get_session(size: int) -> requests.Session:
    session = requests.Session()
    adapter = requests.adapters.HTTPAdapter(pool_connections=size, pool_maxsize=size)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    return session


@lru_cache(maxsize=1)
def get_global_pool(size: int = _max_threads):
    return ThreadPoolExecutor(max_workers=size, thread_name_prefix="GlobalWorker")


@dataclass(frozen=True)
class ArticleSource:
    url: str
    html: str
    crawl_date: datetime
    publisher: Optional[str] = None
    source: Optional["Source"] = None


class Source(Iterable[str], ABC):
    request_header = {"user-agent": "Mozilla/5.0"}

    def __init__(
        self,
        publisher: Optional[str],
        delay: Optional[Callable[[], float]] = None,
    ):
        self.publisher = publisher
        self.delay = delay
        self.max_threads = _max_threads
        self._executor: ThreadPoolExecutor = get_global_pool(_max_threads)
        self._session: requests.Session = get_session(_max_threads)

    @abstractmethod
    def __iter__(self) -> Iterator[str]:
        """
        This should implement an iterator yielding crawled links
        :return: Iterator of links
        """
        raise NotImplementedError

    def _batched_fetch(
        self, url_filter: Optional[UrlFilter] = None
    ) -> Generator[Iterator[Optional[ArticleSource]], int, None]:
        with self._session as session:

            def thread(url: str) -> Optional[ArticleSource]:
                if self.delay:
                    sleep(self.delay())
                try:
                    response = session.get(url=url, headers=self.request_header)
                    response.raise_for_status()
                except (HTTPError, ConnectionError, TooManyRedirects) as error:
                    basic_logger.warn(f"Skipped {url} because of {error}")
                    return None
                except Exception as error:
                    basic_logger.error(f"Run into an unexpected Error while requesting {url}: {error}")
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

            url_iterator: Iterator[str]
            if url_filter:
                url_iterator = filter(_not(url_filter), self)
            else:
                url_iterator = iter(self)
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
                yield self._executor.map(thread, batch_urls)

    def fetch(self, batch_size: Optional[int], url_filter: Optional[UrlFilter]) -> Iterator[ArticleSource]:
        batch_size = batch_size or _max_threads
        self._executor = get_global_pool(min(batch_size, _max_threads))
        self._session = get_session(min(batch_size, _max_threads))
        gen = self._batched_fetch(url_filter)
        while True:
            try:
                next(gen)
                yield from filter(bool, gen.send(batch_size))
            except StopIteration:
                break


class StaticSource(Source):
    def __init__(self, links: List[str], publisher: Optional[str] = None):
        super().__init__(publisher)
        self.links = links

    def __iter__(self):
        yield from self.links


class RSSSource(Source):
    def __init__(self, url: str, publisher: str):
        super().__init__(publisher)
        self.url = url

    def __iter__(self) -> Iterator[str]:
        with requests.Session() as session:
            content = session.get(self.url).content
            rss_feed = feedparser.parse(content)
            if exception := rss_feed.get("bozo_exception"):
                basic_logger.warning(f"Warning! Couldn't parse rss feed at {self.url}. Exception: {exception}")
                return iter(())
            else:
                return (entry["link"] for entry in rss_feed["entries"])


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


class SitemapSource(Source):
    _sitemap_selector: XPath = CSSSelector("sitemap > loc")
    _url_selector: XPath = CSSSelector("url > loc")

    def __init__(
        self,
        sitemap: str,
        publisher: str,
        recursive: bool = True,
        reverse: bool = False,
    ):
        super().__init__(publisher)

        self.sitemap = sitemap
        self.recursive = recursive
        self.reverse = reverse
        self._decompressor = _ArchiveDecompressor()

    def __iter__(self) -> Iterator[str]:
        def yield_recursive(url: str):
            try:
                response = session.get(url=url, headers=self.request_header)
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
                for loc in reversed(sitemap_locs) if self.reverse else sitemap_locs:
                    yield from yield_recursive(loc)

        with requests.Session() as session:
            yield from yield_recursive(self.sitemap)
