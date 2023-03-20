import gzip
from abc import ABC, abstractmethod
from datetime import datetime
from functools import cached_property
from time import sleep
from typing import Callable, Dict, Iterable, Iterator, List, Optional

import feedparser
import lxml.html
import requests

from src.logging.logger import basic_logger
from src.scraping.article import ArticleSource


class Crawler(Iterable[str], ABC):
    def __init__(self, publisher: Optional[str]):
        self.publisher = publisher

    @abstractmethod
    def __iter__(self) -> Iterator[str]:
        """
        This should implement an iterator yielding crawled links
        :return: Iterator of links
        """
        raise NotImplementedError

    def crawl(self, delay: Callable[[], float] = lambda: 0.0) -> Iterator[ArticleSource]:
        with requests.Session() as session:
            for url in self:
                sleep(delay())
                response = session.get(url=url)
                article_source = ArticleSource(
                    url=response.url,
                    html=response.text,
                    crawl_date=datetime.now(),
                    publisher=self.publisher,
                    crawler_ref=self,
                )
                yield article_source


class StaticCrawler(Crawler):
    def __init__(self, links: List[str], publisher: Optional[str] = None):
        super().__init__(publisher)
        self.links = links

    def __iter__(self):
        yield from self.links


class RSSCrawler(Crawler):
    def __init__(self, url: str, publisher: str):
        super().__init__(publisher)
        self.url = url

    def __iter__(self) -> Iterator[str]:
        with requests.Session() as session:
            content = session.get(self.url).content
            rss_feed = feedparser.parse(content)
            if exception := rss_feed.get("bozo_exception"):
                basic_logger.info(f"Warning! Couldn't parse rss feed at {self.url}. Exception: {exception}")
                return iter(())
            else:
                return (entry["link"] for entry in rss_feed["entries"])


class _ArchiveDecompressor:
    def __init__(self):
        self.archive_mapping: Dict[str, Callable[[bytes], bytes]] = {"gz": self._decompress_gzip}

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


class SitemapCrawler(Crawler):
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
            content = session.get(url).content
            if supported_file_format := self._get_archive_format(url):
                content = self._decompressor.decompress(content, supported_file_format)
            tree = lxml.html.fromstring(content)
            urls = [node.text_content() for node in tree.cssselect("url > loc")]
            yield from reversed(urls) if self.reverse else urls
            if self.recursive:
                sitemap_locs = [node.text_content() for node in tree.cssselect("sitemap > loc")]
                for loc in reversed(sitemap_locs) if self.reverse else sitemap_locs:
                    yield from yield_recursive(loc)

        with requests.Session() as session:
            yield from yield_recursive(self.sitemap)
