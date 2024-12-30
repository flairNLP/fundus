from __future__ import annotations

import contextlib
import datetime as dt
import gzip
import itertools
import json
import logging.config
import math
import multiprocessing
import os
import pickle
import random
import re
import threading
import time
import traceback
from abc import ABC, abstractmethod
from functools import lru_cache, partial, wraps
from multiprocessing import Manager
from multiprocessing.context import TimeoutError
from multiprocessing.managers import BaseManager
from multiprocessing.pool import MapResult, Pool, ThreadPool
from pathlib import Path
from queue import Empty, Queue
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Literal,
    Mapping,
    NamedTuple,
    Optional,
    Pattern,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)
from urllib.parse import urljoin, urlparse

import dateutil.rrule as rrule
import dill
import fastwarc.stream_io
import matplotlib.pyplot as plt
import more_itertools
import numpy as np
import requests
import urllib3.exceptions
from more_itertools import roundrobin
from tqdm import tqdm
from typing_extensions import ParamSpec, Self, TypeAlias

from fundus.logging import create_logger, get_current_config
from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.article import Article, Stat
from fundus.scraping.delay import Delay
from fundus.scraping.filter import ExtractionFilter, Requires, RequiresAll, URLFilter
from fundus.scraping.html import HTML, CCNewsSource
from fundus.scraping.scraper import CCNewsScraper, WebScraper
from fundus.scraping.session import session_handler
from fundus.scraping.url import URLSource
from fundus.utils.serialization import JSONVal
from fundus.utils.timeout import Timeout

logger = create_logger(__name__)

_T = TypeVar("_T")
_P = ParamSpec("_P")

PublisherType: TypeAlias = Union[Publisher, PublisherGroup]

_stop_event = threading.Event()


class RemoteException(Exception):
    pass


class TQDMManager(BaseManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.register("_tqdm", tqdm)

    def tqdm(self, *args, **kwargs) -> tqdm:
        return getattr(self, "_tqdm")(*args, **kwargs)


@contextlib.contextmanager
def get_proxy_tqdm(*args, **kwargs) -> tqdm:
    """
    This functions returns a proxy to a tqdm instance. Init args are the same as for any other tqdm instance.
    :param args: tqdm args
    :param kwargs: tqdm kwargs
    :return: a self-managed, proxied tqdm instance
    """
    manager = TQDMManager()
    try:
        manager.start()
        yield manager.tqdm(*args, **kwargs)
    finally:
        manager.shutdown()


# noinspection PyPep8Naming
class dill_wrapper(Generic[_P, _T]):
    def __init__(self, target: Callable[_P, _T]):
        """Wraps function in dill serialization.

        This is in order to use unpickable functions within multiprocessing.

        Args:
            target: The function to wrap.
        """
        self._serialized_target: bytes = dill.dumps(target)

    @lru_cache
    def _deserialize(self) -> Callable[_P, _T]:
        return cast(Callable[_P, _T], dill.loads(self._serialized_target))

    def __call__(self, *args: _P.args, **kwargs: _P.kwargs) -> _T:
        return self._deserialize()(*args, **kwargs)


def get_execution_context():
    """
    Determines whether the current execution context is in a thread or process.
    Returns:
        context (str): "thread" or "process"
        ident (int): Thread ID or Process ID
    """
    if multiprocessing.current_process().name != "MainProcess":
        # In a child process
        current_process = multiprocessing.current_process()
        return current_process.name, current_process.ident
    else:
        # In the main process, check for threading
        current_thread = threading.current_thread()
        return current_thread.name, current_thread.ident


def queue_wrapper(queue: Queue[Union[_T, Exception]], target: Callable[_P, Iterator[_T]]) -> Callable[_P, None]:
    """Wraps the target callable to add its results to the queue instead of returning them directly.

    Args:
        queue: The buffer queue.
        target: A target callable.

    Returns:
        (Callable[_P, None]) The wrapped target.
    """

    @wraps(target)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> None:
        try:
            for obj in target(*args, **kwargs):
                queue.put(obj)
        except Exception as err:
            tb_str = "".join(traceback.TracebackException.from_exception(err).format())
            context, ident = get_execution_context()
            queue.put(
                RemoteException(
                    f"There was a(n) {type(err).__name__!r} occurring in {context} with ident {ident}\n{tb_str}"
                )
            )

    return wrapper


def pool_queue_iter(handle: MapResult[Any], queue: Queue[Union[_T, Exception]]) -> Iterator[_T]:
    """Utility function to iterate exhaustively over a pool queue.

    The underlying iterator of this function repeatedly exhausts the given queue.
    Then, if the queue is empty only if all the pool's jobs have finished, the iterator reruns.
    Otherwise, it waits for the queue to be populated with the next result from the pool.

    Args:
        handle:  A handle of the MappedResult of the underling multiprocessing pool.
        queue: The pool queue.

    Returns:
        Iterator[_T]: The iterator over the queue as it is populated.
    """
    while True:
        try:
            if isinstance(nxt := queue.get_nowait(), Exception):
                raise Exception("There was an exception occurring in a remote thread/process") from nxt
            yield nxt
        except Empty:
            try:
                handle.get(timeout=0.1)
            except TimeoutError:
                if _stop_event.is_set():
                    _stop_event.clear()
                    break
                continue
            return


def random_sleep(func: Callable[_P, _T], between: Tuple[float, float]) -> Callable[_P, _T]:
    @wraps(func)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        time.sleep(random.uniform(*between))
        return func(*args, **kwargs)

    return wrapper


def remove_query_parameters_from_url(url: str) -> str:
    if any(parameter_indicator in url for parameter_indicator in ("?", "#")):
        return urljoin(url, urlparse(url).path)
    return url


class CrawlerBase(ABC):
    def __init__(self, *publishers: PublisherType):
        self.publishers: List[Publisher] = list(set(more_itertools.collapse(publishers)))
        if not self.publishers:
            raise ValueError("param <publishers> of <Crawler.__init__> must include at least one publisher.")

    @abstractmethod
    def _build_article_iterator(
        self,
        publishers: Tuple[Publisher, ...],
        error_handling: Literal["suppress", "catch", "raise"],
        extraction_filter: Optional[ExtractionFilter],
        url_filter: Optional[URLFilter],
    ) -> Iterator[Article]:
        raise NotImplementedError

    def crawl(
        self,
        max_articles: Optional[int] = None,
        timeout: Optional[int] = None,
        error_handling: Literal["suppress", "catch", "raise"] = "suppress",
        only_complete: Union[bool, ExtractionFilter] = Requires("title", "body", "publishing_date"),
        url_filter: Optional[URLFilter] = None,
        only_unique: bool = True,
        save_to_file: Union[None, str, Path] = None,
    ) -> Iterator[Article]:
        """Yields articles from initialized scrapers

        Args:
            max_articles (Optional[int]): Number of articles to crawl. If there are fewer articles
                than max_articles the Iterator will stop before max_articles. If None, all retrievable
                articles are returned. Defaults to None.
            timeout (Optional[int]): timeout (Optional[int]): Specifies the duration in seconds the crawler
                will wait without receiving any articles before stopping. If set <= 0, or if not provided,
                the crawler will run until all sources are exhausted. Defaults to None.
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
            save_to_file (Union[None, str, Path]): If set, the crawled articles will be collected saved to the
                specified file as a JSON list.

        Returns:
            Iterator[Article]: An iterator yielding objects of type Article.
        """

        if max_articles == 0:
            return

        max_articles = max_articles or -1
        timeout = timeout or -1

        def build_extraction_filter() -> Optional[ExtractionFilter]:
            if isinstance(only_complete, bool):
                return None if only_complete is False else RequiresAll()
            else:
                return only_complete

        response_cache: Set[str] = set()

        extraction_filter = build_extraction_filter()
        fitting_publishers: List[Publisher] = []

        if isinstance(extraction_filter, Requires):
            for publisher in self.publishers:
                supported_attributes = set(
                    more_itertools.flatten(
                        collection.names for collection in publisher.parser.attribute_mapping.values()
                    )
                )
                if missing_attributes := extraction_filter.required_attributes - supported_attributes:
                    logger.warning(
                        f"The required attribute(s) `{', '.join(missing_attributes)}` "
                        f"is(are) not supported by {publisher.name}. Skipping publisher"
                    )
                else:
                    fitting_publishers.append(publisher)

            if not fitting_publishers:
                logger.error(
                    f"Could not find any fitting publishers for required attributes  "
                    f"`{', '.join(extraction_filter.required_attributes)}`"
                )
                return
        else:
            fitting_publishers = self.publishers

        article_count = 0
        crawled_articles = []

        # Unfortunately we relly on this little workaround here to terminate the 'Pool' used within
        # the 'CCNewsCrawler'. The 'Timeout' contextmanager utilizes '_thread.interrupt_main',
        # throwing a KeyboardInterrupt in the main thread after <time> seconds. My guess (MaxDall)
        # is, that within 'queue_wrapper's 'handle.get(timeout=0.1)', the main thread cannot be
        # interrupted via a KeyboardInterrupt. The workaround is to have a modul global event
        # that can be set within the 'Timeout' thread using a callback.
        # With Python 3.10 we can pass a signum to '_thread.interrupt_main', maybe that's the way to go.
        callback: Optional[Callable[[], None]]
        if isinstance(self, CCNewsCrawler) and self.processes > 0:

            def callback() -> None:
                _stop_event.set()

        else:
            callback = None

        try:
            with Timeout(seconds=timeout, silent=True, callback=callback, disable=timeout <= 0) as timer:
                for article in self._build_article_iterator(
                    tuple(fitting_publishers), error_handling, build_extraction_filter(), url_filter
                ):
                    timer.reset()
                    url_without_query_parameters = remove_query_parameters_from_url(article.html.responded_url)
                    if not only_unique or url_without_query_parameters not in response_cache:
                        response_cache.add(url_without_query_parameters)
                        article_count += 1
                        if save_to_file is not None:
                            crawled_articles.append(article)
                        yield article
                    if article_count == max_articles:
                        break
        finally:
            session_handler.close_current_session()
            if save_to_file is not None:
                with open(save_to_file, "w", encoding="utf-8") as file:
                    logger.info(f"Writing crawled articles to {save_to_file!r}")
                    file.write(
                        json.dumps(crawled_articles, default=lambda o: o.to_json(), ensure_ascii=False, indent=4)
                    )


class Crawler(CrawlerBase):
    def __init__(
        self,
        *publishers: PublisherType,
        restrict_sources_to: Optional[List[Type[URLSource]]] = None,
        ignore_deprecated: bool = False,
        delay: Optional[Union[float, Delay]] = 1.0,
        threading: bool = True,
        ignore_robots: bool = False,
        ignore_crawl_delay: bool = False,
    ):
        """Fundus base class for crawling articles from the web.

        Examples:
            >>> from fundus import PublisherCollection, Crawler
            >>> crawler = Crawler(*PublisherCollection)
            >>> # Crawler(PublisherCollection.us) to crawl only american news
            >>> for article in crawler.crawl():
            >>>     print(article)

        Args:
            *publishers (Union[Publisher, PublisherGroup]): The publishers to crawl.
            restrict_sources_to (Optional[List[Type[URLSource]]]): Lets you restrict sources defined in the publisher
                specs. If set, only articles from given source types will be yielded.
            ignore_deprecated (bool): If set to True, Publishers marked as deprecated will be skipped.
                Defaults to False.
            delay (Optional[Union[float, Delay]]): Set a delay time in seconds to be used between article
                downloads. You can set a delay directly using float or any callable satisfying the Delay
                protocol. If set to None, no delay will be used between batches. See Delay for more
                information. Defaults to None.
            threading (bool): If True, the crawler will use a dedicated thread per publisher, if set to False,
                the crawler will use a single thread for all publishers and load articles successively. This will
                greatly influence performance, and it is highly recommended to use a threaded crawler.
                Defaults to True.
            ignore_robots (bool): Determines whether to bypass the consideration of the robots.txt file when
                filtering URLs from publishers. If set to True, the URLs will not be filtered based on the
                robots.txt file. Defaults to False.
            ignore_crawl_delay (bool): Determines whether to ignore a crawl delay given by a publisher.
                If set to False, this will overwrite <delay>. If ignore_robots is set to True, the crawl delay
                will also be ignored.
        """

        def filter_publishers(publisher: Publisher) -> bool:
            if publisher.deprecated and ignore_deprecated:
                logger.warning(f"Skipping deprecated publisher: {publisher.name}")
                return False
            return True

        fitting_publishers = list(filter(filter_publishers, more_itertools.collapse(publishers)))
        if not fitting_publishers:
            raise ValueError(
                f"All given publishers are deprecated. Either set <ignore_deprecated> to `False` or "
                f"include at least one publisher that isn't deprecated."
            )

        super().__init__(*fitting_publishers)

        self.restrict_sources_to = restrict_sources_to
        self.delay = delay
        self.threading = threading
        self.ignore_robots = ignore_robots
        self.ignore_crawl_delay = ignore_crawl_delay

    def _fetch_articles(
        self,
        publisher: Publisher,
        error_handling: Literal["suppress", "catch", "raise"],
        extraction_filter: Optional[ExtractionFilter] = None,
        url_filter: Optional[URLFilter] = None,
    ) -> Iterator[Article]:
        def build_delay() -> Optional[Delay]:
            if isinstance(self.delay, float):
                delay = self.delay

                def constant_delay() -> float:
                    return delay

                return constant_delay

            elif isinstance(self.delay, Delay):
                return self.delay

            else:
                raise TypeError("param <delay> of <Crawler.__init__>")

        scraper = WebScraper(
            publisher,
            self.restrict_sources_to,
            build_delay(),
            ignore_robots=self.ignore_robots,
            ignore_crawl_delay=self.ignore_crawl_delay,
        )
        yield from scraper.scrape(error_handling, extraction_filter, url_filter)

    @staticmethod
    def _single_crawl(
        publishers: Tuple[Publisher, ...], article_task: Callable[[Publisher], Iterator[Article]]
    ) -> Iterator[Article]:
        article_iterators = [article_task(publisher) for publisher in publishers]
        yield from roundrobin(*article_iterators)

    @staticmethod
    def _threaded_crawl(
        publishers: Tuple[Publisher, ...], article_task: Callable[[Publisher], Iterator[Article]]
    ) -> Iterator[Article]:
        result_queue: Queue[Union[Article, Exception]] = Queue(len(publishers))
        wrapped_article_task = queue_wrapper(result_queue, article_task)

        with ThreadPool(processes=len(publishers) or None) as pool, session_handler.context(len(publishers), 1):
            yield from pool_queue_iter(pool.map_async(wrapped_article_task, publishers), result_queue)

    def _build_article_iterator(
        self,
        publishers: Tuple[Publisher, ...],
        error_handling: Literal["suppress", "catch", "raise"],
        extraction_filter: Optional[ExtractionFilter],
        url_filter: Optional[URLFilter],
    ) -> Iterator[Article]:
        article_task = partial(
            self._fetch_articles,
            error_handling=error_handling,
            extraction_filter=extraction_filter,
            url_filter=url_filter,
        )

        if self.threading:
            yield from self._threaded_crawl(publishers, article_task)
        else:
            yield from self._single_crawl(publishers, article_task)


class CCNewsCrawler(CrawlerBase):
    def __init__(
        self,
        *publishers: PublisherType,
        start: dt.datetime = dt.datetime(2016, 8, 1),
        end: dt.datetime = dt.datetime.now(),
        processes: int = -1,
        retries: int = 3,
        disable_tqdm: bool = False,
        server_address: str = "https://data.commoncrawl.org/",
    ):
        """Initializes a crawler for the CC-NEWS dataset.

        The crawler crawls the CC-NEWS dataset from <end> to <start>.

        Args:
            *publishers: The publishers to crawl.
            start: The date to start crawling from. Refers to the date the WARC record was added to CC-NEWS,
                not when it was published. Defaults to 2016/8/1.
            end: The date to end crawling. Refers to the date the WARC record was added to CC-NEWS, not when
                it was published. Defaults to datetime.now().
            processes: Number of additional process to use for crawling.
                If -1, the number of processes is set to `os.cpu_count()`.
                If `os.cpu_count()` is not available, the number of processes is set to 0.
                If 0, only the main process is used. Defaults to -1.
            retries: The number of times to retry crawling a WARC record when a connection error occurs. Between
                retries, the crawler sleeps for <current-try> * 30 seconds. Defaults to 3.
            disable_tqdm: Disable the usage of tqdm within the crawler. Defaults to False.
            server_address: The CC-NEWS dataset server address. Defaults to 'https://data.commoncrawl.org/'.
        """

        super().__init__(*publishers)

        self.start = start
        self.end = end

        if processes < 0:
            print(
                f"{type(self).__name__} will automatically use all available cores: {os.cpu_count()}. "
                f"For optimal performance, we recommend manually setting the number of processes "
                f"using the <processes> parameter. A good rule of thumb is to allocate `one process per "
                f"200 Mbps of bandwidth`."
            )
            self.processes = os.cpu_count() or 0
        else:
            self.processes = processes

        self.retries = retries
        self.disable_tqdm = disable_tqdm
        self.server_address = server_address

    def _fetch_articles(
        self,
        warc_path: str,
        publishers: Tuple[Publisher, ...],
        error_handling: Literal["suppress", "catch", "raise"],
        extraction_filter: Optional[ExtractionFilter] = None,
        url_filter: Optional[URLFilter] = None,
        bar: Optional[tqdm] = None,
    ) -> Iterator[Article]:
        retries: int = 0
        while True:
            source = CCNewsSource(*publishers, warc_path=warc_path)
            scraper = CCNewsScraper(source)
            try:
                yield from scraper.scrape(error_handling, extraction_filter, url_filter)
            except (requests.HTTPError, fastwarc.stream_io.StreamError, urllib3.exceptions.HTTPError) as exception:
                if retries >= self.retries:
                    logger.error(f"Failed to load WARC file {warc_path!r} after {retries} retries")
                    break
                else:
                    retries += 1
                    sleep_time = (30 * retries) + random.uniform(-2, 2)
                    logger.warning(
                        f"Could not load WARC file {warc_path!r}. Retry after {sleep_time:.2f} seconds: {exception!r}"
                    )
                    time.sleep(sleep_time)
            else:
                break

        if bar is not None:
            bar.update()

    @staticmethod
    def _single_crawl(
        warc_paths: Tuple[str, ...], article_task: Callable[[str], Iterator[Article]]
    ) -> Iterator[Article]:
        for warc_path in warc_paths:
            yield from article_task(warc_path)

    def _parallel_crawl(
        self, warc_paths: Tuple[str, ...], article_task: Callable[[str], Iterator[Article]]
    ) -> Iterator[Article]:
        # because logging configurations are overwritten when using 'spawn' as start method,
        # we have to get current logging configurations and initialize them in the new process
        if multiprocessing.get_start_method() == "spawn":
            logging_config = get_current_config()
            initializer = partial(logging.config.dictConfig, config=logging_config)
        else:
            initializer = None

        # As one could think, because we're downloading a bunch of files, this task is IO-bound, but it is actually
        # process-bound. The reason is that we stream the data and process it on the fly rather than downloading all
        # files and processing them afterward. Therefore, we utilize multiprocessing here instead of multithreading.
        with Manager() as manager, Pool(
            processes=min(self.processes, len(warc_paths)),
            initializer=initializer,
        ) as pool:
            result_queue: Queue[Union[Article, Exception]] = manager.Queue(maxsize=1000)

            # Because multiprocessing.Pool does not support iterators as targets,
            # we wrap the article_task to write the articles to a queue instead of returning them directly.
            wrapped_article_task: Callable[[str], None] = queue_wrapper(result_queue, article_task)

            # To avoid 503 errors we spread tasks to not start all at once
            spread_article_task = random_sleep(wrapped_article_task, (0, 3))

            # To avoid restricting the article_task to use only pickleable objects, we serialize it using dill.
            serialized_article_task = dill_wrapper(spread_article_task)

            # Finally, we build an iterator around the queue, exhausting the queue until the pool is finished.
            yield from pool_queue_iter(pool.map_async(serialized_article_task, warc_paths), result_queue)

    def _get_warc_paths(self) -> List[str]:
        # Date regex examples: https://regex101.com/r/yDX3G6/1
        date_pattern: Pattern[str] = re.compile(r"CC-NEWS-(?P<date>\d{14})-")

        if self.start >= self.end:
            raise ValueError("Start date has to be < end date.")

        if self.start < dt.datetime(2016, 8, 1):
            raise ValueError("The default, and earliest possible, start date is 2016/08/01.")

        if self.end > dt.datetime.now():
            raise ValueError("The specified end date is in the future. We don't want to give spoilers, do we?")

        date_sequence: List[dt.datetime] = list(rrule.rrule(rrule.MONTHLY, dtstart=self.start, until=self.end))
        urls: List[str] = [
            f"{self.server_address}crawl-data/CC-NEWS/{date.strftime('%Y/%m')}/warc.paths.gz" for date in date_sequence
        ]

        with tqdm(total=len(urls), desc="Loading WARC Paths", leave=False, disable=self.disable_tqdm) as bar:

            def load_paths(url: str) -> List[str]:
                with requests.Session() as session:
                    paths = gzip.decompress(session.get(url).content).decode("utf-8").split()
                    bar.update()
                    return paths

            if self.processes == 0:
                nested_warc_paths = [load_paths(url) for url in urls]
            else:
                # use two threads per process, default two threads per core
                max_number_of_threads = self.processes * 2

                with ThreadPool(processes=min(len(urls), max_number_of_threads)) as pool:
                    nested_warc_paths = pool.map(random_sleep(load_paths, (0, 3)), urls)

        warc_paths: Iterator[str] = more_itertools.flatten(nested_warc_paths)

        start_strf = self.start.strftime("%Y%m%d%H%M%S")
        end_strf = self.end.strftime("%Y%m%d%H%M%S")

        def filter_warc_path_by_date(path: str) -> bool:
            match: Optional[re.Match[str]] = date_pattern.search(path)
            if match is None:
                raise AssertionError(f"Invalid WARC path {path!r}")
            return start_strf <= match["date"] <= end_strf

        return sorted(
            (f"{self.server_address}{warc_path}" for warc_path in filter(filter_warc_path_by_date, warc_paths)),
            reverse=True,
        )

    def _build_article_iterator(
        self,
        publishers: Tuple[Publisher, ...],
        error_handling: Literal["suppress", "catch", "raise"],
        extraction_filter: Optional[ExtractionFilter],
        url_filter: Optional[URLFilter],
        **kwargs,
    ) -> Iterator[Article]:
        warc_paths = tuple(self._get_warc_paths())

        with get_proxy_tqdm(total=len(warc_paths), desc="Process WARC files", disable=self.disable_tqdm) as bar:
            article_task = partial(
                self._fetch_articles,
                publishers=publishers,
                error_handling=error_handling,
                extraction_filter=extraction_filter,
                url_filter=url_filter,
                bar=bar,
            )

            if self.processes == 0:
                yield from self._single_crawl(warc_paths, article_task)
            else:
                yield from self._parallel_crawl(warc_paths, article_task)

    def benchmark(
        self, sample_rate: int = rrule.MONTHLY, sample_size: Optional[int] = 1000, keep_html: bool = True
    ) -> Benchmark:
        if sample_rate > rrule.DAILY:
            raise ValueError("Sample rate < rrule.DAILY are not supported")

        benchmark = Benchmark(*self.publishers, keep_html=keep_html)

        dates = list(rrule.rrule(freq=sample_rate, dtstart=self.start, until=self.end))

        # TODO: add date filter
        for date in tqdm(reversed(dates), total=len(dates), desc="samples", position=0, disable=self.disable_tqdm):
            crawler = CCNewsCrawler(*self.publishers, start=date, end=date + dt.timedelta(days=1), disable_tqdm=True)

            for article in tqdm(
                crawler.crawl(max_articles=sample_size, only_complete=False),
                total=sample_size,
                desc="articles",
                position=1,
                leave=False,
                disable=self.disable_tqdm,
            ):
                benchmark.add(article)

        return benchmark


class Entry(NamedTuple):
    stat: Stat
    html: Optional[HTML] = None

    def __repr__(self) -> str:
        return f"{self.stat!r}"


class Series(List[Entry]):
    def __init__(self):
        super().__init__()

    @property
    def avg(self) -> float:
        return sum(entry.stat.completeness for entry in self) / len(self)

    def __repr__(self) -> str:
        return f"{self.avg:.2%}"


class TimeFrame(Dict[str, Series]):
    def __init__(self, *publishers: str, keep_html: bool = True):
        super().__init__({publisher: Series() for publisher in publishers})
        self._keep_html = keep_html

    def add(self, article: Article):
        self[article.publishers].append(Entry(article.complete, article.html if self._keep_html else None))

    def squeeze(self, threshold: float) -> Self:
        for publisher, series in self.items():
            tmp = Series()
            for entry in series:
                if entry.stat.completeness <= threshold:
                    tmp.append(entry)
            self[publisher] = tmp
        return self

    def reduce(self, percentage: float) -> Self:
        new_length = math.ceil(len(self) * percentage)
        while len(self) > new_length:
            max_list = sorted(self.values(), key=len, reverse=True)[0]
            max_list.pop()
        return self

    def trim(self, max_length: int) -> Self:
        for publisher, series in self.items():
            if len(series) <= max_length:
                continue
            random.shuffle(series)
            self[publisher] = series[:max_length]
        return self

    def __len__(self) -> int:
        return sum(len(entries) for entries in self.values())


class Benchmark(Dict[dt.date, TimeFrame]):
    def __init__(self, *publishers: Publisher, keep_html: bool = True):
        self.keep_html = keep_html
        self._publishers = {publisher.name for publisher in publishers}
        super().__init__()

    def add(self, article: Article):
        record = self[article.html.crawl_date.date()]
        record.add(article)

    def squeeze(self, threshold: float) -> Self:
        for frame in self.values():
            frame.squeeze(threshold)
        return self

    def reduce(self, percentage: float) -> Self:
        for frame in self.values():
            frame.reduce(percentage)
        return self

    def trim(self, max_length: int) -> Self:
        for frame in self.values():
            frame.trim(max_length)
        return self

    def save(self, path: Union[Path, str]) -> None:
        with gzip.open(path, "wb") as file:
            file.write(pickle.dumps(self))

    @classmethod
    def load(cls, path: Union[Path, str]) -> Benchmark:
        with gzip.open(path, "rb") as file:
            return pickle.loads(file.read())

    def plot(self, path: Union[Path, str]) -> None:
        fig, ax = plt.subplots()
        ax.plot(self)

    def __len__(self) -> int:
        return sum(len(record) for record in self.values())

    def __missing__(self, key: dt.date) -> TimeFrame:
        new = TimeFrame(*self._publishers, keep_html=self.keep_html)
        self[key] = new
        return new
