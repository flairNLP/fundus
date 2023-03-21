from abc import ABC, abstractmethod
from datetime import datetime
from multiprocessing.pool import ThreadPool
from time import sleep
from typing import Callable, Generator, Iterable, Iterator, List, Optional

import feedparser
import lxml.html
import requests
from requests import HTTPError

from src.logging.logger import basic_logger
from src.scraping.article import ArticleSource
from src.utils.error_states import error_stated, Failed, Succeeded, Result


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

    def _batched_fetch(self) -> Generator[List[Result], int, None]:
        with requests.Session() as session:
            it = iter(self)

            @error_stated(HTTPError)
            def thread(url: str) -> ArticleSource:
                if self.delay:
                    sleep(self.delay())
                response = session.get(url=url, headers=self.request_header)
                response.raise_for_status()
                article_source = ArticleSource(
                    url=response.url,
                    html=response.text,
                    crawl_date=datetime.now(),
                    publisher=self.publisher,
                    crawler_ref=self,
                )
                return article_source

            empty = False
            with ThreadPool(processes=self.max_threads) as pool:
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

    def fetch(self, batch_size: int = 10) -> Iterator[ArticleSource]:
        gen = self._batched_fetch()
        while True:
            try:
                next(gen)
                batch = gen.send(batch_size)
                for element in batch:
                    if isinstance(element, Failed):
                        basic_logger.info(f"Skipped {element.args[0]} because of {element.exception}")
                    elif isinstance(element, Succeeded):
                        yield element.result
                    else:
                        raise TypeError(f"Found unexpected object type {type(element)}")
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
                basic_logger.info(f"Warning! Couldn't parse rss feed at {self.url}. Exception: {exception}")
                return iter(())
            else:
                return (entry["link"] for entry in rss_feed["entries"])


class SitemapSource(Source):
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

    def config(self, recursive: bool, reverse: bool):
        self.recursive = recursive
        self.reverse = reverse

    def __iter__(self) -> Iterator[str]:
        def yield_recursive(url: str):
            response = session.get(url=url, headers=self.request_header)
            response.raise_for_status()
            tree = lxml.html.fromstring(response.content)
            urls = [node.text_content() for node in tree.cssselect("url > loc")]
            yield from reversed(urls) if self.reverse else urls
            if self.recursive:
                sitemap_locs = [node.text_content() for node in tree.cssselect("sitemap > loc")]
                for loc in reversed(sitemap_locs) if self.reverse else sitemap_locs:
                    yield from yield_recursive(loc)

        with requests.Session() as session:
            yield from yield_recursive(self.sitemap)
