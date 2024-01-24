from __future__ import annotations

import gzip
import os
import re
from datetime import datetime
from functools import lru_cache, partial, wraps
from multiprocessing import Manager
from multiprocessing.context import TimeoutError
from multiprocessing.pool import MapResult, Pool, ThreadPool
from queue import Empty, Queue
from typing import (
    Any,
    Callable,
    Generic,
    Iterator,
    List,
    Literal,
    Optional,
    Pattern,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
)

import dill
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
_P = ParamSpec("P")


# noinspection PyPep8Naming
class dill_wrapper(Generic[_P, _T]):
    def __init__(self, target: Callable[_P, _T]):
        """Wraps function in dill serialization.

        This is in order to use unpickable functions within multiprocessing.

        Args:
            target (Callable[P, _T): The function to wrap.
        """
        self._serialized_target: bytes = dill.dumps(target)

    @lru_cache
    def _deserialize(self) -> Callable[_P, _T]:
        return cast(Callable[_P, _T], dill.loads(self._serialized_target))

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _T:
        return self._deserialize()(*args, **kwargs)


def queue_wrapper(queue: Queue[_T], target: Callable[_P, Iterator[_T]]) -> Callable[_P, None]:
    """Wraps the target callable to add its results to the queue instead of returning them directly.

    Args:
        queue: (Queue[_T]) The buffer queue.
        target: (Callable[P, Iterator[_T]]) A target callable.

    Returns:
        (Callable[P, None]) The wrapped target.
    """

    @wraps(target)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> None:
        for obj in target(*args, **kwargs):
            queue.put(obj)

    return wrapper


class CCNewsCrawler:
    def __init__(
        self,
        *publishers: PublisherEnum,
        processes: int = -1,
        server_address: str = "https://data.commoncrawl.org/",
    ):
        """Initializes a crawler for the CC-NEWS dataset.

        Args:
            *publishers (PublisherEnum): The publishers to crawl.
            processes: Number of additional process to use for crawling.
                If -1, the number of processes is set to `os.cpu_count()`.
                If `os.cpu_count()` is not available, the number of processes is set to 0.
                If 0, only the main process is used. Defaults to -1.
            server_address: The CC-NEWS dataset server address. Defaults to 'https://data.commoncrawl.org/'.
        """
        self.publishers = publishers
        self.processes = os.cpu_count() or 0 if processes == -1 else processes
        self.server_address = server_address

    def _get_warc_paths(self, start: datetime, end: datetime) -> List[str]:
        # https://regex101.com/r/yDX3G6/1
        date_pattern: Pattern[str] = re.compile(r"CC-NEWS-(?P<date>\d{14})-")

        if start >= end:
            raise ValueError("Start date has to be < end date.")

        if start < datetime(2016, 8, 1):
            raise ValueError("The default, and earliest possible, start date is 2016/08/01.")

        if end > datetime.now():
            raise ValueError("The specified end date is in the future. We don't want to give spoilers, do we?")

        date_sequence: List[datetime] = list(rrule(MONTHLY, dtstart=start, until=end))
        urls: List[str] = [
            f"{self.server_address}crawl-data/CC-NEWS/{date.strftime('%Y/%m')}/warc.paths.gz" for date in date_sequence
        ]

        def load_paths(url: str) -> List[str]:
            with requests.Session() as session:
                return gzip.decompress(session.get(url).content).decode("utf-8").split()

        # running two threads per core
        max_number_of_threads = 2 * (os.cpu_count() or 1)

        with ThreadPool(processes=min(len(urls), max_number_of_threads)) as pool:
            warc_paths = more_itertools.flatten(
                list(
                    tqdm(pool.imap_unordered(load_paths, urls), total=len(urls), desc="Loading WARC paths", leave=False)
                )
            )

        start_strf = start.strftime("%Y%m%d%H%M%S")
        end_strf = end.strftime("%Y%m%d%H%M%S")

        def filter_warc_path_by_date(path: str) -> bool:
            match: Optional[re.Match[str]] = date_pattern.search(path)
            if match is None:
                raise AssertionError(f"Invalid WARC path {path!r}")
            return start_strf <= match["date"] <= end_strf

        return sorted(
            (f"{self.server_address}{warc_path}" for warc_path in filter(filter_warc_path_by_date, warc_paths)),
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
        yield from scraper.scrape(error_handling, extraction_filter, url_filter)

    @staticmethod
    def _single_crawl(warc_paths: List[str], article_task: Callable[[str], Iterator[Article]]) -> Iterator[Article]:
        for warc_path in warc_paths:
            yield from article_task(warc_path)

    def _parallel_crawl(
        self, warc_paths: List[str], article_task: Callable[[str], Iterator[Article]]
    ) -> Iterator[Article]:
        # As one could think, because we're downloading a bunch of files, this task is IO bound, but it is actually
        # process bound. The reason for this is that we stream the data and process it on the fly rather than
        # downloading all files and processing them afterward. Therefore, we utilize multiprocessing here instead
        # of multithreading.
        with Manager() as manager, Pool(processes=min(self.processes, len(warc_paths))) as pool:
            article_queue: Queue[Article] = manager.Queue()

            # Because multiprocessing.Pool does not support iterators as targets we wrap the article_task to pass
            # the articles to a queue instead of returning them directly.
            wrapped_article_task: Callable[[str], None] = queue_wrapper(article_queue, article_task)

            # To avoid restricting article_task to use only pickable objects we serialize it using dill.
            serialized_article_task = dill_wrapper(wrapped_article_task)

            # Finally, we build an iterator around the queue, exhausting the queue and handling if the pool
            # is finished.
            yield from pool_queue_iter(pool.map_async(serialized_article_task, warc_paths), article_queue)

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

        This method provides the same functionality as the fundus standard crawler,
        except this one fetches articles from the CC-News corpus.
        Specify a date range from <start> to <end> to fetch only articles crawled in this range.
        The default range is 2016/8/1 -> datetime.now().
        These dates correspond to the crawl date of the CC-News crawler, not the publishing date.
        To filter on publishing dates, use the <only_complete> parameter and refer to the docs about filtering articles.

        Args:
            start: (datetime): Earliest possible crawl date for retrieved articles. Defaults to 2016/8/1.
            end: (datetime): Latest possible crawl date for retrieved articles. Defaults to datetime.now().
            max_articles (Optional[int]): Number of articles to crawl. If there are fewer articles
                than max_articles the Iterator will stop before max_articles. If None, all retrievable
                articles are returned. Defaults to None.
            error_handling (Literal["suppress", "catch", "raise"]): Define how to handle errors
                encountered during extraction. If set to "suppress", all errors will be skipped, either
                with None values for respective attributes in the extraction or by skipping entire articles.
                If set to "catch", errors will be caught as attribute values or, if an entire article fails,
                through Article.exception. If set to "raise", all errors encountered during extraction will
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

        if max_articles is None:
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

        warc_paths = self._get_warc_paths(start, end)
        response_cache: Set[str] = set()

        article_task: Callable[[str], Iterator[Article]] = partial(
            self._fetch_articles,
            publishers=self.publishers,
            error_handling=error_handling,
            extraction_filter=build_extraction_filter(),
            url_filter=url_filter,
        )

        if self.processes == 0:
            article_iter = self._single_crawl(warc_paths, article_task)
        else:
            article_iter = self._parallel_crawl(warc_paths, article_task)

        for article_idx, article in enumerate(article_iter, start=1):
            if not only_unique or article.html.responded_url not in response_cache:
                response_cache.add(article.html.responded_url)
                yield article
            if article_idx == max_articles:
                break


def pool_queue_iter(handle: MapResult[Any], queue: Queue[_T]) -> Iterator[_T]:
    while True:
        try:
            yield queue.get(timeout=0.1)
        except Empty:
            try:
                handle.get(timeout=0.1)
            except TimeoutError:
                continue
            return
