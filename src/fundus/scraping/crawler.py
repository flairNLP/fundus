from __future__ import annotations

import gzip
import os
import re
from abc import ABC, abstractmethod
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
    Type,
    TypeVar,
    Union,
    cast,
)
from urllib.parse import urljoin, urlparse

import dill
import more_itertools
import requests
from dateutil.rrule import MONTHLY, rrule
from more_itertools import roundrobin
from tqdm import tqdm
from typing_extensions import ParamSpec, TypeAlias

from fundus.logging import create_logger
from fundus.publishers.base_objects import PublisherCollectionMeta, PublisherEnum
from fundus.scraping.article import Article
from fundus.scraping.delay import Delay
from fundus.scraping.filter import ExtractionFilter, Requires, RequiresAll, URLFilter
from fundus.scraping.html import CCNewsSource
from fundus.scraping.scraper import CCNewsScraper, WebScraper
from fundus.scraping.session import session_handler
from fundus.scraping.url import URLSource

logger = create_logger(__name__)

_T = TypeVar("_T")
_P = ParamSpec("_P")

Publisher: TypeAlias = Union[PublisherEnum, Type[PublisherEnum], PublisherCollectionMeta]


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


def queue_wrapper(queue: Queue[_T], target: Callable[_P, Iterator[_T]]) -> Callable[_P, None]:
    """Wraps the target callable to add its results to the queue instead of returning them directly.

    Args:
        queue: The buffer queue.
        target: A target callable.

    Returns:
        (Callable[_P, None]) The wrapped target.
    """

    @wraps(target)
    def wrapper(*args: _P.args, **kwargs: _P.kwargs) -> None:
        for obj in target(*args, **kwargs):
            queue.put(obj)

    return wrapper


def pool_queue_iter(handle: MapResult[Any], queue: Queue[_T]) -> Iterator[_T]:
    """Utility function to iterate exhaustively over a pool queue.

    The underlying iterator of this function repeatedly exhausts the given queue.
    Then, if the queue is empty only if all the pool's jobs have finished, the iterator reruns.
    Otherwise, it waits for the queue to be populated with the next result from the pool.

    Args:
        handle (MapResult[Any]):  A handle o the MappedResult of the underling multiprocessing pool.
        queue (Queue[_T]): The pool queue.

    Returns:
        Iterator[_T]: The iterator over the queue as it is populated.
    """
    while True:
        try:
            yield queue.get(timeout=0.1)
        except Empty:
            try:
                handle.get(timeout=0.1)
            except TimeoutError:
                continue
            return


def remove_query_parameters_from_url(url: str) -> str:
    if any(parameter_indicator in url for parameter_indicator in ("?", "#")):
        return urljoin(url, urlparse(url).path)
    return url


class CrawlerBase(ABC):
    def __init__(self, *publishers: Publisher):
        if not publishers:
            raise ValueError("param <publishers> of <Crawler.__init__> has to be non empty")

        self.publishers: List[PublisherEnum] = list(set(more_itertools.collapse(publishers)))

    @abstractmethod
    def _build_article_iterator(
        self,
        publishers: Tuple[PublisherEnum, ...],
        error_handling: Literal["suppress", "catch", "raise"],
        extraction_filter: Optional[ExtractionFilter],
        url_filter: Optional[URLFilter],
    ) -> Iterator[Article]:
        raise NotImplementedError

    def crawl(
        self,
        max_articles: Optional[int] = None,
        error_handling: Literal["suppress", "catch", "raise"] = "suppress",
        only_complete: Union[bool, ExtractionFilter] = Requires("title", "body", "publishing_date"),
        url_filter: Optional[URLFilter] = None,
        only_unique: bool = True,
    ) -> Iterator[Article]:
        """Yields articles from initialized scrapers

        Args:
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

        if max_articles is None:
            max_articles = -1

        def build_extraction_filter() -> Optional[ExtractionFilter]:
            if isinstance(only_complete, bool):
                return None if only_complete is False else RequiresAll()
            else:
                return only_complete

        response_cache: Set[str] = set()

        extraction_filter = build_extraction_filter()
        fitting_publishers: List[PublisherEnum] = []

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
                        f"is(are) not supported by {publisher.publisher_name}. Skipping publisher"
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
        for article in self._build_article_iterator(
            tuple(fitting_publishers), error_handling, build_extraction_filter(), url_filter
        ):
            url_without_query_parameters = remove_query_parameters_from_url(article.html.responded_url)
            if not only_unique or url_without_query_parameters not in response_cache:
                response_cache.add(url_without_query_parameters)
                article_count += 1
                yield article
            if article_count == max_articles:
                break

        session_handler.close_current_session()


class Crawler(CrawlerBase):
    def __init__(
        self,
        *publishers: Publisher,
        restrict_sources_to: Optional[List[Type[URLSource]]] = None,
        delay: Optional[Union[float, Delay]] = 1.0,
        threading: bool = True,
    ):
        """Fundus base class for crawling articles from the web.

        Examples:
            >>> from fundus import PublisherCollection, Crawler
            >>> crawler = Crawler(*PublisherCollection)
            >>> # Crawler(PublisherCollection.us) to crawl only american news
            >>> for article in crawler.crawl():
            >>>     print(article)

        Args:
            *publishers (Union[PublisherEnum, Type[PublisherEnum], PublisherCollectionMeta]): The publishers to crawl.
            restrict_sources_to (Optional[List[Type[URLSource]]]): Lets you restrict
                sources defined in the publisher specs. If set, only articles from given source types
                will be yielded.
            delay (Optional[Union[float, Delay]]): Set a delay time in seconds to be used between article
                downloads. You can set a delay directly using float or any callable satisfying the Delay
                protocol. If set to None, no delay will be used between batches. See Delay for more
                information. Defaults to None.
            threading (bool): If True, the crawler will use a dedicated thread per publisher, if set to False,
                the crawler will use a single thread for all publishers and load articles successively. This will greatly
                influence performance, and it is highly recommended to use a threaded crawler. Deafults to True.
        """

        super().__init__(*publishers)

        self.restrict_sources_to = restrict_sources_to
        self.delay = delay
        self.threading = threading

    def _fetch_articles(
        self,
        publisher: PublisherEnum,
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

        scraper = WebScraper(publisher, self.restrict_sources_to, build_delay())
        yield from scraper.scrape(error_handling, extraction_filter, url_filter)

    @staticmethod
    def _single_crawl(
        publishers: Tuple[PublisherEnum, ...], article_task: Callable[[PublisherEnum], Iterator[Article]]
    ) -> Iterator[Article]:
        article_iterators = [article_task(publisher) for publisher in publishers]
        yield from roundrobin(*article_iterators)

    @staticmethod
    def _threaded_crawl(
        publishers: Tuple[PublisherEnum, ...], article_task: Callable[[PublisherEnum], Iterator[Article]]
    ) -> Iterator[Article]:
        article_queue: Queue[Article] = Queue(len(publishers))
        wrapped_article_task = queue_wrapper(article_queue, article_task)

        with ThreadPool(processes=len(publishers) or None) as pool, session_handler.context(len(publishers), 1):
            yield from pool_queue_iter(pool.map_async(wrapped_article_task, publishers), article_queue)

    def _build_article_iterator(
        self,
        publishers: Tuple[PublisherEnum, ...],
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
        *publishers: Publisher,
        start: datetime = datetime(2016, 8, 1),
        end: datetime = datetime.now(),
        processes: int = -1,
        server_address: str = "https://data.commoncrawl.org/",
    ):
        """Initializes a crawler for the CC-NEWS dataset.

        Args:
            *publishers: The publishers to crawl.
            processes: Number of additional process to use for crawling.
                If -1, the number of processes is set to `os.cpu_count()`.
                If `os.cpu_count()` is not available, the number of processes is set to 0.
                If 0, only the main process is used. Defaults to -1.
            server_address: The CC-NEWS dataset server address. Defaults to 'https://data.commoncrawl.org/'.
        """

        super().__init__(*publishers)

        self.start = start
        self.end = end
        self.processes = os.cpu_count() or 0 if processes == -1 else processes
        self.server_address = server_address

    @staticmethod
    def _fetch_articles(
        warc_path: str,
        publishers: Tuple[PublisherEnum, ...],
        error_handling: Literal["suppress", "catch", "raise"],
        extraction_filter: Optional[ExtractionFilter] = None,
        url_filter: Optional[URLFilter] = None,
    ) -> Iterator[Article]:
        source = CCNewsSource(*publishers, warc_path=warc_path)
        scraper = CCNewsScraper(source)
        yield from scraper.scrape(error_handling, extraction_filter, url_filter)

    @staticmethod
    def _single_crawl(
        warc_paths: Tuple[str, ...], article_task: Callable[[str], Iterator[Article]]
    ) -> Iterator[Article]:
        for warc_path in warc_paths:
            yield from article_task(warc_path)

    def _parallel_crawl(
        self, warc_paths: Tuple[str, ...], article_task: Callable[[str], Iterator[Article]]
    ) -> Iterator[Article]:
        # As one could think, because we're downloading a bunch of files, this task is IO-bound, but it is actually
        # process-bound. The reason is that we stream the data and process it on the fly rather than downloading all
        # files and processing them afterward. Therefore, we utilize multiprocessing here instead of multithreading.
        with Manager() as manager, Pool(processes=min(self.processes, len(warc_paths))) as pool:
            article_queue: Queue[Article] = manager.Queue(maxsize=1000)

            # Because multiprocessing.Pool does not support iterators as targets,
            # we wrap the article_task to write the articles to a queue instead of returning them directly.
            wrapped_article_task: Callable[[str], None] = queue_wrapper(article_queue, article_task)

            # To avoid restricting the article_task to use only pickleable objects, we serialize it using dill.
            serialized_article_task = dill_wrapper(wrapped_article_task)

            # Finally, we build an iterator around the queue, exhausting the queue until the pool is finished.
            yield from pool_queue_iter(pool.map_async(serialized_article_task, warc_paths), article_queue)

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

        with tqdm(total=len(urls), desc="Loading WARC Paths", leave=False) as bar:

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
                    nested_warc_paths = pool.map(load_paths, urls)

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
        publishers: Tuple[PublisherEnum, ...],
        error_handling: Literal["suppress", "catch", "raise"],
        extraction_filter: Optional[ExtractionFilter],
        url_filter: Optional[URLFilter],
    ) -> Iterator[Article]:
        warc_paths = tuple(self._get_warc_paths())

        article_task = partial(
            self._fetch_articles,
            publishers=publishers,
            error_handling=error_handling,
            extraction_filter=extraction_filter,
            url_filter=url_filter,
        )

        if self.processes == 0:
            yield from self._single_crawl(warc_paths, article_task)
        else:
            yield from self._parallel_crawl(warc_paths, article_task)
