from __future__ import annotations

import gzip
import logging.config
import multiprocessing
import os
import random
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from functools import partial
from multiprocessing import Manager, Pool
from multiprocessing.pool import ThreadPool
from typing import Callable, Iterator, List, Optional, Pattern, Tuple

import more_itertools
import requests
from dateutil.rrule import MONTHLY, rrule
from tqdm import tqdm

from fundus.logging import create_logger, get_current_config
from fundus.publishers.base_objects import Publisher
from fundus.scraping.article import Article
from fundus.scraping.crawler.base import CrawlerBase, PublisherType
from fundus.scraping.crawler.queueing import (
    enqueue_results,
    iter_pool_results,
)
from fundus.scraping.filter import ExtractionFilter, URLFilter
from fundus.scraping.pipeline import Pipeline
from fundus.scraping.pipeline.source.ccnews import CCNewsSource, WarcFileLoadError
from fundus.scraping.session import session_handler
from fundus.utils.concurrency import dill_wrapper, get_proxy_tqdm
from fundus.utils.events import __EVENTS__, __MAIN_THREAD_ALIAS__
from fundus.utils.timing import random_sleep

logger = create_logger(__name__)


class CCNewsCrawler(CrawlerBase):
    """Crawler for the CC-NEWS archive: extracts articles from Common Crawl's monthly WARC files.

    Resolves the WARC paths covering the requested date range, then processes each archive with a
    CCNewsSource-backed Pipeline. Runs across multiple processes by default; WARC downloads are
    retried on transient errors.
    """

    def __init__(
        self,
        *publishers: PublisherType,
        start: datetime = datetime(2016, 8, 1),
        end: Optional[datetime] = None,
        processes: int = -1,
        retries: int = 3,
        disable_tqdm: bool = False,
        server_address: str = "https://data.commoncrawl.org/",
    ):
        """Initializes a crawler for the CC-NEWS dataset.

        Args:
            *publishers: The publishers to crawl.
            start: Start date for WARC records. Defaults to 2016/8/1.
            end: End date for WARC records. Defaults to datetime.now().
            processes: Number of additional processes. -1 uses all CPU cores. Defaults to -1.
            retries: Retry count on connection errors. Defaults to 3.
            disable_tqdm: Disable tqdm progress bars. Defaults to False.
            server_address: CC-NEWS server address.
        """
        super().__init__(*publishers)

        self.start = start
        self.end = end if end is not None else datetime.now()

        if start >= self.end:
            raise ValueError("Start date has to be < end date.")
        if start < datetime(2016, 8, 1):
            raise ValueError("The default, and earliest possible, start date is 2016/08/01.")
        if self.end > datetime.now():
            raise ValueError("The specified end date is in the future.")

        if processes < 0:
            logger.warning(
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

    def _on_timeout(self) -> None:
        """Set the main-thread-aliased stop event on timeout."""
        if self.processes > 0:
            __EVENTS__.set_event("stop", __MAIN_THREAD_ALIAS__)

    def _fetch_articles(
        self,
        warc_path: str,
        publishers: Tuple[Publisher, ...],
        raise_on_error: bool,
        extraction_filter: Optional[ExtractionFilter] = None,
        url_filter: Optional[URLFilter] = None,
        language_filter: Optional[List[str]] = None,
        bar: Optional[tqdm] = None,
    ) -> Iterator[Article]:
        """Process one WARC file through a pipeline, retrying on WarcFileLoadError up to self.retries."""
        retries: int = 0
        while True:
            pipeline = Pipeline(
                CCNewsSource(*publishers, warc_path=warc_path),
                publishers=publishers,
            )
            try:
                yield from pipeline.run(raise_on_error, extraction_filter, url_filter, language_filter)
            except WarcFileLoadError as exception:
                if retries >= self.retries:
                    logger.error(f"Failed to load WARC file {warc_path!r} after {retries} retries")
                    break
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
        """Process every WARC path sequentially in the calling process (no multiprocessing)."""
        for warc_path in warc_paths:
            yield from article_task(warc_path)

    def _parallel_crawl(
        self, warc_paths: Tuple[str, ...], article_task: Callable[[str], Iterator[Article]]
    ) -> Iterator[Article]:
        """Process WARC paths across a process pool, funnelling articles through a managed queue."""
        if multiprocessing.get_start_method() == "spawn":
            logging_config = get_current_config()
            initializer = partial(logging.config.dictConfig, config=logging_config)
        else:
            initializer = None

        with Manager() as manager, Pool(
            processes=min(self.processes, len(warc_paths)),
            initializer=initializer,
        ) as pool:
            result_queue = manager.Queue(maxsize=1000)
            wrapped_task = enqueue_results(result_queue, article_task)
            spread_task = random_sleep(wrapped_task, (0, 3))
            serialized_task = dill_wrapper(spread_task)
            yield from iter_pool_results(pool.map_async(serialized_task, warc_paths), result_queue)
            logger.debug(f"Shutting down {type(self).__name__!r} ...")

    def _get_warc_paths(self) -> List[str]:
        """Resolve and return the WARC archive URLs covering [start, end], newest first."""
        date_pattern: Pattern[str] = re.compile(r"CC-NEWS-(?P<date>\d{14})-")

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
                max_threads = self.processes * 2
                with ThreadPool(processes=min(len(urls), max_threads)) as pool:
                    nested_warc_paths = pool.map(random_sleep(load_paths, (0, 3)), urls)

        warc_paths_iter = more_itertools.flatten(nested_warc_paths)
        start_strf = self.start.strftime("%Y%m%d%H%M%S")
        end_strf = self.end.strftime("%Y%m%d%H%M%S")

        def filter_by_date(path: str) -> bool:
            match = date_pattern.search(path)
            if match is None:
                raise AssertionError(f"Invalid WARC path {path!r}")
            return start_strf <= match["date"] <= end_strf

        return sorted(
            (f"{self.server_address}{p}" for p in filter(filter_by_date, warc_paths_iter)),
            reverse=True,
        )

    def _build_article_iterator(
        self,
        publishers: Tuple[Publisher, ...],
        raise_on_error: bool,
        extraction_filter: Optional[ExtractionFilter],
        url_filter: Optional[URLFilter],
        language_filter: Optional[List[str]],
        skip_publishers_disallowing_training: bool = False,
    ) -> Iterator[Article]:
        """Yield articles from the CC-NEWS archive backend: optionally drop publishers that disallow training,
        resolve the WARC paths covering the date range, then dispatch them to the sequential or multi-process crawl.
        """
        if skip_publishers_disallowing_training:
            max_workers = self.processes if self.processes > 0 else min(len(publishers), 5)
            verified_publishers: List[Publisher] = []

            with ThreadPoolExecutor(max_workers=max_workers) as executor, session_handler.context(timeout=10):
                future_to_publisher = {
                    executor.submit(lambda p: p.disallows_training, publisher): publisher for publisher in publishers
                }

                # resolve warc paths within the ThreadPoolExecutor context
                warc_paths = tuple(self._get_warc_paths())

                for future in as_completed(future_to_publisher):
                    publisher = future_to_publisher[future]
                    try:
                        if not future.result():
                            verified_publishers.append(publisher)
                        else:
                            logger.warning(f"Skipping publisher {publisher.name!r} because it disallows training.")
                    except Exception as exc:
                        logger.warning(f"Could not verify training policy for {publisher.name!r}: {exc}", exc_info=True)
            publishers = tuple(verified_publishers)
        else:
            warc_paths = tuple(self._get_warc_paths())

        with get_proxy_tqdm(total=len(warc_paths), desc="Process WARC files", disable=self.disable_tqdm) as bar:
            article_task = partial(
                self._fetch_articles,
                publishers=publishers,
                raise_on_error=raise_on_error,
                extraction_filter=extraction_filter,
                url_filter=url_filter,
                language_filter=language_filter,
                bar=bar,
            )
            if self.processes == 0:
                yield from self._single_crawl(warc_paths, article_task)
            else:
                yield from self._parallel_crawl(warc_paths, article_task)
