from __future__ import annotations

import contextlib
import threading
from functools import partial, wraps
from multiprocessing.pool import ThreadPool
from queue import Queue
from typing import Callable, Iterator, List, Optional, Tuple, Type, Union

import more_itertools
from more_itertools import roundrobin

from fundus.logging import create_logger
from fundus.publishers.base_objects import Publisher
from fundus.scraping.article import Article
from fundus.scraping.crawler.base import CrawlerBase, PublisherType, supports_attributes
from fundus.scraping.crawler.queueing import enqueue_results, iter_pool_results
from fundus.scraping.delay import Delay, Pacer, RobotsCrawlDelay
from fundus.scraping.filter import ExtractionFilter, URLFilter
from fundus.scraping.pipeline import Pipeline
from fundus.scraping.pipeline.source.interleaved import InterleavedSource
from fundus.scraping.pipeline.source.web import WebSource
from fundus.scraping.session import CrashThread
from fundus.scraping.url import URLSource
from fundus.utils.events import __EVENTS__

logger = create_logger(__name__)


def publisher_context_wrapper(func: Callable[[Publisher], None]) -> Callable[[Publisher], None]:
    """Wraps a callable to register an ``__EVENTS__`` alias context for the publisher argument.

    The alias is entered as the very first thing the thread does and stays alive for the
    entire call — including any exception handling in the caller — so that
    ``__EVENTS__.get_alias`` always resolves while the thread is running.

    Args:
        func: A callable whose first positional argument is a :class:`Publisher`.

    Returns:
        The wrapped callable.
    """

    @wraps(func)
    def wrapper(publisher: Publisher) -> None:
        with __EVENTS__.context(publisher.name):
            func(publisher)

    return wrapper


class Crawler(CrawlerBase):
    """Crawler for the live web: fetches articles by requesting each publisher's URL sources.

    Builds one Pipeline per batch of a publisher's URL sources (see SourceHandler.batches), drawing
    the sources of a batch in turn, and, when threading is enabled, runs one thread per publisher.
    Honors robots.txt and crawl delays, pacing each publisher as a whole.
    """

    def __init__(
        self,
        *publishers: PublisherType,
        restrict_sources_to: Optional[List[Type[URLSource]]] = None,
        ignore_deprecated: bool = False,
        delay: Optional[Union[int, float, Delay]] = 1.0,
        threading: bool = True,
        ignore_robots: bool = False,
        ignore_crawl_delay: bool = False,
        impersonate: bool = False,
    ):
        """Crawler for fetching articles from the web.

        Examples:
            >>> from fundus import PublisherCollection, Crawler
            >>> crawler = Crawler(*PublisherCollection)
            >>> for article in crawler.crawl():
            >>>     print(article)

        Args:
            *publishers: The publishers to crawl.
            restrict_sources_to: Restrict sources to the given URL source types.
            ignore_deprecated: Skip deprecated publishers. Defaults to False.
            delay: Delay in seconds between article downloads. Defaults to 1.0.
            threading: Use one thread per publisher. Defaults to True.
            ignore_robots: Bypass robots.txt filtering. Defaults to False.
            ignore_crawl_delay: Ignore crawl-delay from robots.txt. Defaults to False.
            impersonate: If True, publishers that declare an `impersonate` browser profile
                will use curl_cffi's TLS/HTTP fingerprint impersonation. If False (default),
                the profile is ignored and requests go out with Fundus' regular fingerprint —
                publishers gated by anti-bot checks will likely return 4xx/5xx. Defaults to False.
        """

        fitting_publishers = []
        for publisher in more_itertools.collapse(publishers):
            if publisher.deprecated and ignore_deprecated:
                logger.warning(f"Skipping deprecated publisher: {publisher.name}")
            else:
                fitting_publishers.append(publisher)
        if not fitting_publishers:
            raise ValueError(
                "All given publishers are deprecated. Either set <ignore_deprecated> to `False` or "
                "include at least one publisher that isn't deprecated."
            )

        # restricted here, since <restrict_sources_to> arrives with the crawler and holds for every
        # crawl it runs. Publishers left without a source are reported per crawl rather than raising,
        # together with the ones a crawl's own restrictions rule out.
        super().__init__(*(publisher.restrict(source_types=restrict_sources_to) for publisher in fitting_publishers))

        self.restrict_sources_to = restrict_sources_to
        self.threading = threading
        self.ignore_robots = ignore_robots
        self.ignore_crawl_delay = ignore_crawl_delay
        self.impersonate = impersonate

        self._delay = self._resolve_delay(delay)

    @staticmethod
    def _resolve_delay(delay: Optional[Union[int, float, Delay]]) -> Optional[Delay]:
        """Normalize the delay argument into a Delay callable (or None); wraps a constant in a thunk."""
        if delay is None:
            return None
        if isinstance(delay, (int, float)):

            def constant_delay() -> float:
                return delay

            return constant_delay
        if callable(delay):
            return delay
        raise TypeError("param <delay> of <Crawler.__init__> must be float, Delay, or None")

    def _supports_attributes(self, publisher: Publisher, extraction_filter: Optional[ExtractionFilter]) -> bool:
        """The live web is always parsed with the version valid today."""
        return supports_attributes(extraction_filter, [publisher.parser.latest_version])

    def _publisher_pacer(self, publisher: Publisher, stop_event: threading.Event) -> Pacer:
        """Build the pacer shared by all of <publisher>'s sources.

        A crawl-delay declared in the publisher's robots.txt overrides the crawler's delay, unless
        robots.txt or the crawl-delay it declares is ignored. Setting <stop_event> interrupts a delay.
        """
        delay = self._delay
        if not (self.ignore_robots or self.ignore_crawl_delay):
            delay = RobotsCrawlDelay(publisher.robots, publisher.request_header.get("user-agent", "*"), default=delay)
        return Pacer(delay, sleep=stop_event.wait)

    def _build_pipelines(self, publisher: Publisher) -> List[Pipeline]:
        """Build one Pipeline per batch of the (restricted) publisher's URL sources, in crawl order.

        All of the publisher's WebSources share one pacer, so that the delay paces the publisher
        rather than each source separately. Without this, drawing a batch of n sources in turn would
        fire n requests before any of them waits.
        """
        stop_event = __EVENTS__.get("stop")
        pacer = self._publisher_pacer(publisher, stop_event)

        def build(url_source: URLSource) -> WebSource:
            return WebSource(
                url_source=url_source,
                publisher=publisher,
                url_filter=publisher.url_filter,
                query_parameters=publisher.query_parameter,
                ignore_robots=self.ignore_robots,
                impersonate=self.impersonate,
                stop_event=stop_event,
                pacer=pacer,
            )

        return [
            Pipeline(InterleavedSource(*(build(url_source) for url_source in batch)), publishers=[publisher])
            for batch in publisher.sources.batches()
        ]

    def _on_publisher_limit_reached(self, publisher_name: str) -> None:
        """Set the publisher's stop event so its thread halts once the per-publisher limit is hit."""
        if self.threading and not __EVENTS__.is_event_set("stop", publisher_name):
            __EVENTS__.set_event("stop", publisher_name)

    def _fetch_articles(
        self,
        publisher: Publisher,
        raise_on_error: bool,
        extraction_filter: Optional[ExtractionFilter] = None,
        url_filter: Optional[URLFilter] = None,
        skip_publishers_disallowing_training: bool = False,
    ) -> Iterator[Article]:
        """Run every pipeline for one publisher, yielding its articles.

        Skips the publisher if training is disallowed and that is asked for, or if its robots.txt
        disallows all URLs, unless robots.txt is ignored.
        """
        if skip_publishers_disallowing_training and publisher.disallows_training:
            logger.info(f"Skipping publisher {publisher.name} because it disallows training.")
            return
        # <ignore_robots> goes first, so that an ignored robots.txt is never requested
        elif not self.ignore_robots and publisher.robots.disallow_all():
            logger.info(f"Skipping publisher {publisher.name} because it disallows all URLs.")
            return

        for pipeline in self._build_pipelines(publisher):
            yield from pipeline.run(raise_on_error, extraction_filter, url_filter)

    @staticmethod
    def _single_crawl(
        publishers: Tuple[Publisher, ...], article_task: Callable[[Publisher], Iterator[Article]]
    ) -> Iterator[Article]:
        """Round-robin articles from all publishers in the calling thread (no threading)."""
        yield from roundrobin(*[article_task(publisher) for publisher in publishers])

    @contextlib.contextmanager
    def _thread_pool(self, processes: int) -> Iterator[ThreadPool]:
        """Yield a ThreadPool, signalling all publisher threads to stop and joining them on exit."""
        pool = ThreadPool(processes or None)
        try:
            yield pool
        finally:
            logger.debug(f"Shutting down {type(self).__name__!r} ...")
            pool.close()
            __EVENTS__.set_for_all("stop", future=True, active_only=True)
            pool.join()
            __EVENTS__.clear_for_all("stop")
            logger.debug("Shutdown done")

    def _threaded_crawl(
        self, publishers: Tuple[Publisher, ...], article_task: Callable[[Publisher], Iterator[Article]]
    ) -> Iterator[Article]:
        """Run one publisher per pool thread, funnelling their articles through a shared queue."""
        result_queue: Queue[Union[Article, Exception]] = Queue(len(publishers))
        wrapped_task = publisher_context_wrapper(
            enqueue_results(result_queue, article_task, silenced_exceptions=(CrashThread,))
        )

        with self._thread_pool(len(publishers)) as pool:
            yield from iter_pool_results(pool.map_async(wrapped_task, publishers), result_queue)

    def _build_article_iterator(
        self,
        publishers: Tuple[Publisher, ...],
        raise_on_error: bool,
        extraction_filter: Optional[ExtractionFilter],
        url_filter: Optional[URLFilter],
        skip_publishers_disallowing_training: bool = False,
    ) -> Iterator[Article]:
        """Yield articles from the live-web backend: bind the per-publisher article task,
        then dispatch the publishers to the threaded or single-threaded crawl.
        """
        article_task = partial(
            self._fetch_articles,
            raise_on_error=raise_on_error,
            extraction_filter=extraction_filter,
            url_filter=url_filter,
            skip_publishers_disallowing_training=skip_publishers_disallowing_training,
        )
        if self.threading:
            yield from self._threaded_crawl(publishers, article_task)
        else:
            yield from self._single_crawl(publishers, article_task)
