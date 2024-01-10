from __future__ import annotations

import gzip
import os
import re
from datetime import datetime
from functools import partial
from multiprocessing import Manager
from multiprocessing.context import TimeoutError
from multiprocessing.pool import MapResult, Pool, ThreadPool
from queue import Empty, Queue
from typing import (
    Any,
    Callable,
    Iterable,
    Iterator,
    List,
    Literal,
    Optional,
    Pattern,
    Set,
    Tuple,
    TypeVar,
    Union,
)

import more_itertools
import requests
from dateutil.rrule import MONTHLY, rrule
from tqdm import tqdm
from typing_extensions import ParamSpec

from fundus.publishers.base_objects import PublisherEnum
from fundus.scraping.article import Article
from fundus.scraping.common_crawl.html import CCNewsSource
from fundus.scraping.common_crawl.scraper import CCNewsScraper
from fundus.scraping.filter import ExtractionFilter, Requires, URLFilter

_T = TypeVar("_T")
P = ParamSpec("P")


class CCNewsCrawler:
    def __init__(
        self,
        *publishers: PublisherEnum,
        processes: Optional[int] = None,
        server_address: str = "https://data.commoncrawl.org/",
    ):
        """Initializes a crawler for crawling the CC-NEWS dataset.

        Args:
            *publishers (PublisherEnum): The publishers to crawl.
            processes: Number of process to use for crawling. If None, use os.cpu_count(); if -1 omit multiprocessing
                entirely. Defaults to None
            server_address: The CC-NEWS dataset server address. Defaults to 'https://data.commoncrawl.org/'
        """
        self.publishers = publishers
        self.processes = processes or os.cpu_count() or -1
        self.server_address = server_address

    def _get_list_of_warc_path(self, start: datetime, end: datetime) -> List[str]:
        date_pattern: Pattern[str] = re.compile(r"CC-NEWS-(?P<date>\d{14})-\d{5}")

        if start >= end:
            raise ValueError("Start date has to be < end date.")

        if start < datetime(2016, 8, 1):
            raise ValueError("The default, and earliest possible, start date is 2016/08/01.")

        if end > datetime.now():
            raise ValueError("The specified end date lays in the future. We don't want to spoiler, do we?")

        date_sequence: List[datetime] = [dt for dt in rrule(MONTHLY, dtstart=start, until=end)]
        urls = [
            self.server_address + f"crawl-data/CC-NEWS/{date.strftime('%Y/%m')}/warc.paths.gz" for date in date_sequence
        ]

        def load_paths(url: str) -> List[str]:
            with requests.Session() as session:
                paths = gzip.decompress(session.get(url).content).decode("utf-8").split()
                bar.update()
                return paths

        with ThreadPool(processes=len(urls)) as pool, tqdm(total=len(urls), desc="Load WARC paths", leave=False) as bar:
            warc_paths = more_itertools.flatten(pool.map(load_paths, urls))

        start_strf = start.strftime("%Y%m%d%H%M%S")
        end_strf = end.strftime("%Y%m%d%H%M%S")

        def filter_warc_path_by_date(path: str) -> bool:
            if match := date_pattern.search(path):
                return start_strf <= match["date"] <= end_strf
            else:
                return False

        return sorted(
            [self.server_address + warc_path for warc_path in filter(filter_warc_path_by_date, warc_paths)],
            reverse=True,
        )

    @staticmethod
    def _fetch_articles(
        warc_path: str,
        publishers: Tuple[PublisherEnum],
        error_handling: Literal["suppress", "catch", "raise"],
        extraction_filter: Optional[ExtractionFilter] = None,
        url_filter: Optional[URLFilter] = None,
    ) -> Iterator[Article]:
        source = CCNewsSource(*publishers, warc_path=warc_path)
        scraper = CCNewsScraper(source)
        for article in scraper.scrape(error_handling, extraction_filter, url_filter):
            yield article

    @staticmethod
    def _wrapper(*args, queue: Queue[_T], target: Callable[P, Iterator[_T]], **kwargs) -> None:
        for obj in target(*args, **kwargs):
            queue.put(obj)

    @staticmethod
    def _queue_wrapper(
        queue: Queue[_T],
        target: Callable[P, Iterator[_T]],
    ) -> Callable[P, None]:
        return partial(CCNewsCrawler._wrapper, queue=queue, target=target)

    @staticmethod
    def _single_crawl(warc_paths: List[str], target: Callable[[str], Iterator[Article]]) -> Iterator[Article]:
        for warc_path in warc_paths:
            yield from target(warc_path)

    def _parallel_crawl(self, warc_paths: List[str], target: Callable[[str], Iterator[Article]]) -> Iterator[Article]:
        with Manager() as manager, Pool(processes=min(self.processes, len(warc_paths))) as pool:
            article_queue: Queue[Article] = manager.Queue()
            wrapped_target: Callable[[str], None] = self._queue_wrapper(article_queue, target)
            yield from _PoolResult(pool.map_async(wrapped_target, warc_paths), article_queue)

    def crawl(
        self,
        start: datetime = datetime(2016, 8, 1),
        end: datetime = datetime.now(),
        max_articles: Optional[int] = None,
        error_handling: Literal["suppress", "catch", "raise"] = "suppress",
        only_complete: Union[bool, ExtractionFilter] = Requires("title", "body", "publishing_date"),
        url_filter: Optional[URLFilter] = None,
        only_unique: bool = True,
    ) -> Iterator[Article]:
        """Yields articles crawled from the CC-NEWS server.

        Same functionality as fundus standard crawler except this one fetches articles from the
        CC-News corpus.
        One can specify a date range from <start> to <end> to fetch only articles crawled in this range.
        The default range is 2016/8 -> datetime.now()
        This corresponds to the crawl date of the CC-News crawler, not the publishing date.
        To filter on publishing dates use the <only_complete> parameter and refer to the docs about
        filtering articles.

        Args:
            start: (datetime): Earliest possible crawl date for retrieved articles. Defaults to 2016/8/1
            end: (datetime): Latest possible crawl date for retrieved articles. Defaults to datetime.now()
            max_articles (Optional[int]): Number of articles to crawl. If there are fewer articles
                than max_articles the Iterator will stop before max_articles. If None, all retrievable
                articles are returned. Defaults to None.
            error_handling (Literal["suppress", "catch", "raise"]): Define how to handle errors
                encountered during extraction. If set to "suppress", all errors will be skipped, either
                with None values for respective attributes in the extraction or by skipping entire articles.
                If set to "catch", errors will be caught as attribute values or, if an entire article fails,
                through Article.exception. If set to "raise" all errors encountered during extraction will
                be raised. Defaults to "suppress".
            only_complete (Union[bool, ExtractionFilter]): Set a callable satisfying the ExtractionFilter
                protocol as an extraction filter or use a boolean. If False, all articles will be yielded,
                if True, only those with all attributes extracted. Defaults to ExtractionFilter letting
                through all articles with at least title, body, and publishing_date set.
            url_filter (Optional[URLFilter]): A callable object satisfying the URLFilter protocol to skip
                URLs before download. This filter applies on both requested and responded URL. Defaults to None.
            only_unique (bool): If set to True, articles yielded will be unique on the responded URL.
                Always returns the first encountered article. Defaults to True.

        Returns:
            Iterator[Article]: An iterator yielding objects of type Article.
        """

        if max_articles == 0:
            return
        elif max_articles is None:
            max_articles = -1

        def build_extraction_filter() -> Optional[ExtractionFilter]:
            if isinstance(only_complete, bool):
                return (
                    None
                    if only_complete is False
                    else lambda extracted: not all(
                        bool(v) if not isinstance(v, Exception) else False for _, v in extracted.items()
                    )
                )
            else:
                return only_complete

        warc_paths = self._get_list_of_warc_path(start, end)
        response_cache: Set[str] = set()

        article_task: Callable[[str], Iterator[Article]] = partial(
            self._fetch_articles,
            publishers=self.publishers,
            error_handling=error_handling,
            extraction_filter=build_extraction_filter(),
            url_filter=url_filter,
        )

        if self.processes == -1:
            article_iter = self._single_crawl(warc_paths, article_task)
        else:
            article_iter = self._parallel_crawl(warc_paths, article_task)

        for article_idx, article in enumerate(article_iter, start=1):
            if not only_unique or article.html.responded_url not in response_cache:
                response_cache.add(article.html.responded_url)
                yield article
            if article_idx == max_articles:
                break


class _PoolResult(Iterable[_T]):
    def __init__(self, result: MapResult[Any], queue: Queue[_T]):
        """Utility class to iterate a pool queue.

        Exhaust the queue given with <queue>. If <queue> raises Empty and the pool finished,
        raise StopIteration, otherwise continue to wait for the next result from <queue>.

        Args:
            result (MapResult[Any]): A MapResult returned by a Pool.map/.map_async call to use as a handle.
            queue (Queue[_T): The queue to exhaust.
        """
        self._handle = result
        self._queue = queue

    def __next__(self) -> _T:
        while True:
            try:
                return self._queue.get(timeout=0.1)
            except Empty:
                try:
                    self._handle.get(timeout=0.1)
                except TimeoutError:
                    continue
                else:
                    break
        raise StopIteration

    def __iter__(self) -> Iterator[_T]:
        return self
