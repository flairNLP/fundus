from __future__ import annotations

import contextlib
import gzip
import json
import logging.config
import multiprocessing
import os
import random
import re
import time
import traceback
from abc import ABC, abstractmethod
from collections import defaultdict
from datetime import datetime
from functools import lru_cache, partial, wraps
from multiprocessing import Manager
from multiprocessing.context import TimeoutError
from multiprocessing.managers import BaseManager
from multiprocessing.pool import MapResult, Pool, ThreadPool
from pathlib import Path
from queue import Empty, Queue
from threading import current_thread
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Literal,
    Optional,
    Pattern,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)

import dill
import fastwarc.stream_io
import more_itertools
import requests
import urllib3.exceptions
from dateutil.rrule import MONTHLY, rrule
from more_itertools import roundrobin
from tqdm import tqdm
from typing_extensions import ParamSpec, TypeAlias

from fundus.logging import create_logger, get_current_config
from fundus.parser.data import remove_query_parameters_from_url
from fundus.publishers.base_objects import FilteredPublisher, Publisher, PublisherGroup
from fundus.scraping.article import Article
from fundus.scraping.delay import Delay
from fundus.scraping.filter import ExtractionFilter, Requires, RequiresAll, URLFilter
from fundus.scraping.html import CCNewsSource
from fundus.scraping.scraper import CCNewsScraper, WebScraper
from fundus.scraping.session import session_handler
from fundus.scraping.url import URLSource
from fundus.utils.events import __EVENTS__
from fundus.utils.timeout import Timeout

logger = create_logger(__name__)

_T = TypeVar("_T")
_P = ParamSpec("_P")

PublisherType: TypeAlias = Union[Publisher, PublisherGroup]


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
        process = multiprocessing.current_process()
        return process.name, process.ident
    else:
        thread = current_thread()
        return thread.name, thread.ident


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

            logger.debug(f"Encountered remote exception: {err!r}")
            # prevents a race condition where the ThreadPool shuts down before the exception is pulled from the queue
            time.sleep(0.2)

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
                if __EVENTS__.is_event_set("stop"):
                    __EVENTS__.clear_event("stop")
                    break
                continue
            return


def random_sleep(func: Callable[_P, _T], between: Tuple[float, float]) -> Callable[_P, _T]:
    @wraps(func)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> _T:
        time.sleep(random.uniform(*between))
        return func(*args, **kwargs)

    return wrapper


class CrawlerBase(ABC):
    def __init__(self, *publishers: PublisherType):
        self.publishers: List[Union[Publisher, FilteredPublisher]] = list(set(more_itertools.collapse(publishers)))
        if not self.publishers:
            raise ValueError("param <publishers> of <Crawler.__init__> must include at least one publisher.")

        __EVENTS__.alias("main-thread")
        __EVENTS__.register_event("stop")

    @abstractmethod
    def _build_article_iterator(
        self,
        publishers: Tuple[Publisher, ...],
        error_handling: Literal["suppress", "catch", "raise"],
        extraction_filter: Optional[ExtractionFilter],
        url_filter: Optional[URLFilter],
        language_filter: Optional[List[str]],
    ) -> Iterator[Article]:
        raise NotImplementedError

    def crawl(
        self,
        max_articles: Optional[int] = None,
        max_articles_per_publisher: Optional[int] = None,
        timeout: Optional[int] = None,
        error_handling: Literal["suppress", "catch", "raise"] = "suppress",
        only_complete: Union[bool, ExtractionFilter] = Requires("title", "body", "publishing_date"),
        url_filter: Optional[URLFilter] = None,
        language_filter: Optional[List[str]] = None,
        only_unique: bool = True,
        save_to_file: Union[None, str, Path] = None,
    ) -> Iterator[Article]:
        """Yields articles from initialized scrapers

        Args:
            max_articles (Optional[int]): Number of articles to crawl. If there are fewer articles
                than max_articles the Iterator will stop before max_articles. If None, all retrievable
                articles are returned. Defaults to None.
            max_articles_per_publisher: Specify the number of articles to crawl per publisher.
                Disables <max_articles>. Defaults to None.
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
            language_filter (Optional[List[str]]): A set of language codes to filter the articles by. If set,
                articles of different languages will be skipped and not counted towards the article count. Defaults
                to None.
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

        if max_articles_per_publisher:
            if timeout < 120:
                print(
                    "It is recommended to set a minimum <timeout> of 120 seconds when using "
                    "max_articles_per_publisher."
                )
            max_articles = -1

        def build_extraction_filter() -> Optional[ExtractionFilter]:
            if isinstance(only_complete, bool):
                return None if only_complete is False else RequiresAll()
            else:
                return only_complete

        response_cache: Set[str] = set()

        extraction_filter = build_extraction_filter()
        fitting_publishers: List[Union[Publisher, FilteredPublisher]] = []

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
                elif language_filter and not publisher.supports(languages=language_filter):
                    logger.warning(
                        f"None of the required language(s) `{', '.join(language_filter)}` "
                        f"is(are) supported by {publisher.name}. Skipping publisher"
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

        # check if there are filtered publishers and if so, adopt their language restrictions
        publisher_language_filter = set()
        for publisher in fitting_publishers:
            if isinstance(publisher, FilteredPublisher):
                publisher_language_filter.update(publisher.language_filter)

        if language_filter and publisher_language_filter:
            language_filter = list(set(language_filter).union(publisher_language_filter))
            logger.info(
                f"Publisher language filter: {publisher_language_filter} will be added to the given language filter: "
                f"{language_filter}. "
            )
        elif publisher_language_filter:
            language_filter = list(publisher_language_filter)
            logger.info(f"Publisher language filter: {publisher_language_filter} will be used as the language filter. ")

        article_count: Dict[str, int] = defaultdict(int)
        crawled_articles: Dict[str, List[Article]] = defaultdict(list)

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
                __EVENTS__.set_event("stop", "main-thread")

        else:
            callback = None

        try:
            with Timeout(seconds=timeout, silent=True, callback=callback, disable=timeout <= 0) as timer:
                for article in self._build_article_iterator(
                    tuple(fitting_publishers), error_handling, build_extraction_filter(), url_filter, language_filter
                ):
                    if max_articles_per_publisher and article_count[article.publisher] == max_articles_per_publisher:
                        if isinstance(self, Crawler) and not __EVENTS__.is_event_set("stop", article.publisher):
                            __EVENTS__.set_event("stop", article.publisher)
                        if sum(article_count.values()) == len(self.publishers) * max_articles_per_publisher:
                            break
                        continue
                    timer.reset()
                    url_without_query_parameters = remove_query_parameters_from_url(article.html.responded_url)
                    if not only_unique or url_without_query_parameters not in response_cache:
                        response_cache.add(url_without_query_parameters)
                        article_count[article.publisher] += 1
                        if save_to_file:
                            crawled_articles[article.publisher].append(article)
                        yield article
                    if sum(article_count.values()) == max_articles:
                        break
        finally:
            session_handler.close_current_session()
            if save_to_file is not None:
                if isinstance(save_to_file, str):
                    save_to_file = Path(save_to_file)
                save_to_file.parent.mkdir(parents=True, exist_ok=True)
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
        language_filter: Optional[List[str]] = None,
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
        if not scraper.sources and self.restrict_sources_to:
            logger.warning(
                f"No sources of type {[source_type.__name__ for source_type in self.restrict_sources_to]} found for publisher {publisher.name}. "
                f"Skipping publisher."
            )
            return
        yield from scraper.scrape(error_handling, extraction_filter, url_filter, language_filter)

    @staticmethod
    def _single_crawl(
        publishers: Tuple[Publisher, ...], article_task: Callable[[Publisher], Iterator[Article]]
    ) -> Iterator[Article]:
        article_iterators = [article_task(publisher) for publisher in publishers]
        yield from roundrobin(*article_iterators)

    def _threaded_crawl(
        self, publishers: Tuple[Publisher, ...], article_task: Callable[[Publisher], Iterator[Article]]
    ) -> Iterator[Article]:
        result_queue: Queue[Union[Article, Exception]] = Queue(len(publishers))
        wrapped_article_task = queue_wrapper(result_queue, article_task)
        pool = ThreadPool(processes=len(publishers) or None)
        try:
            with session_handler.context(
                POOL_CONNECTIONS=len(publishers),
            ):
                yield from pool_queue_iter(pool.map_async(wrapped_article_task, publishers), result_queue)
        finally:
            logger.debug(f"Shutting down {type(self).__name__!r} ...")
            __EVENTS__.set_for_all("stop")
            pool.close()
            pool.join()
            __EVENTS__.clear_for_all("stop")
            logger.debug("Shutdown done")

    def _build_article_iterator(
        self,
        publishers: Tuple[Publisher, ...],
        error_handling: Literal["suppress", "catch", "raise"],
        extraction_filter: Optional[ExtractionFilter],
        url_filter: Optional[URLFilter],
        language_filter: Optional[List[str]],
    ) -> Iterator[Article]:
        article_task = partial(
            self._fetch_articles,
            error_handling=error_handling,
            extraction_filter=extraction_filter,
            url_filter=url_filter,
            language_filter=language_filter,
        )

        if self.threading:
            yield from self._threaded_crawl(publishers, article_task)
        else:
            yield from self._single_crawl(publishers, article_task)


class CCNewsCrawler(CrawlerBase):
    def __init__(
        self,
        *publishers: PublisherType,
        start: datetime = datetime(2016, 8, 1),
        end: datetime = datetime.now(),
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
        language_filter: Optional[List[str]] = None,
        bar: Optional[tqdm] = None,
    ) -> Iterator[Article]:
        retries: int = 0
        while True:
            source = CCNewsSource(*publishers, warc_path=warc_path)
            scraper = CCNewsScraper(source)
            try:
                yield from scraper.scrape(error_handling, extraction_filter, url_filter, language_filter)
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
        try:
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
        finally:
            logger.debug(f"Shutting down {type(self).__name__!r} ...")
            logger.debug("Joining manager ...")
            manager.join()
            logger.debug("Joining pool ...")
            pool.join()
            logger.debug("Shutdown done")

    def _get_warc_paths(self) -> List[str]:
        # Date regex examples: https://regex101.com/r/yDX3G6/1
        date_pattern: Pattern[str] = re.compile(r"CC-NEWS-(?P<date>\d{14})-")

        if self.start >= self.end:
            raise ValueError("Start date has to be < end date.")

        if self.start < datetime(2016, 8, 1):
            raise ValueError("The default, and earliest possible, start date is 2016/08/01.")

        if self.end > datetime.now():
            raise ValueError("The specified end date is in the future. We don't want to give spoilers, do we?")

        date_sequence: List[datetime] = list(rrule(MONTHLY, dtstart=self.start, until=self.end))
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

                try:
                    with ThreadPool(processes=min(len(urls), max_number_of_threads)) as pool:
                        nested_warc_paths = pool.map(random_sleep(load_paths, (0, 3)), urls)
                finally:
                    pool.join()

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
        language_filter: Optional[List[str]],
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
                language_filter=language_filter,
                bar=bar,
            )

            if self.processes == 0:
                yield from self._single_crawl(warc_paths, article_task)
            else:
                yield from self._parallel_crawl(warc_paths, article_task)
