import gzip
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from functools import cached_property
from multiprocessing.pool import ThreadPool
from time import sleep
from typing import Callable, Dict, Generator, Iterable, Iterator, List, Optional

import feedparser
import lxml.html
import requests
from lxml.cssselect import CSSSelector
from lxml.etree import XPath
from requests import HTTPError

from fundus.classification import UrlClassifier
from fundus.logging.logger import basic_logger


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
            self, publisher: Optional[str], delay: Optional[Callable[[], float]] = None, max_threads: Optional[int] = 10
    ):
        self.publisher = publisher
        self.delay = delay
        self.max_threads = max_threads

    @abstractmethod
    def __iter__(self) -> Iterator[str]:
        """
        This should implement an iterator yielding crawled links
        :return: Iterator of links
        """
        raise NotImplementedError

    def _batched_fetch(self, url_classifier: Optional[UrlClassifier] = None) -> Generator[
        List[Optional[ArticleSource]], int, None]:
        print(f'{url_classifier} at batched fetch')
        with requests.Session() as session:

            def thread(url: str) -> Optional[ArticleSource]:
                if self.delay:
                    sleep(self.delay())
                try:
                    response = session.get(url=url, headers=self.request_header)
                    response.raise_for_status()
                except HTTPError as error:
                    basic_logger.info(f"Skipped {url} because of {error}")
                    return None
                if history := response.history:
                    basic_logger.info(f"Got redirected {len(history)} time(s) from {url} -> {response.url}")

                if url_classifier and not url_classifier(url):
                    basic_logger.info(f'\n{url} got skipped because it is invalid.')
                    return None

                article_source = ArticleSource(
                    url=response.url,
                    html=response.text,
                    crawl_date=datetime.now(),
                    publisher=self.publisher,
                    source=self,
                )
                return article_source

            with ThreadPool(processes=self.max_threads) as pool:
                it = iter(self)
                empty = False
                while not empty:
                    current_size = batch_size = yield  # type: ignore
                    batch_urls = []
                    while current_size > 0 and (nxt := next(it, None)):
                        batch_urls.append(nxt)
                        current_size -= 1
                    if not batch_urls:
                        break
                    elif len(batch_urls) < batch_size:
                        empty = True
                    yield pool.map(thread, batch_urls)

    def fetch(self, batch_size: int = 10, url_classifier: Optional[UrlClassifier] = None) -> Iterator[ArticleSource]:
        print(f'{url_classifier} at fetch')
        gen = self._batched_fetch(url_classifier)
        while True:
            try:
                next(gen)
                yield from filter(lambda x: bool(x), gen.send(batch_size))
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

    def config(self, recursive: bool, reverse: bool):
        self.recursive = recursive
        self.reverse = reverse

    def _get_archive_format(self, url: str) -> Optional[str]:
        if "." in url and (file_format := url.split(".")[-1]) in self._decompressor.supported_file_formats:
            return file_format
        else:
            return None

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
