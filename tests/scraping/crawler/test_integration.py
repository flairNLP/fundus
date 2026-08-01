from __future__ import annotations

import io
import logging
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator
from unittest.mock import patch

import pytest

from fundus import Crawler
from fundus.logging import _BATCH_CAPACITY, add_handler, remove_handler, set_log_level
from fundus.scraping.article import Article
from fundus.scraping.crawler import CCNewsCrawler
from fundus.scraping.html import HTML, SourceInfo
from fundus.scraping.pipeline import Pipeline
from fundus.utils.timeout import _interrupt_handler
from tests.fixtures.builders import make_article, make_html
from tests.fixtures.fakes import FakeCrawler

# More than one batch worth, with a remainder that only the end-of-work flush can deliver.
_CHATTER = _BATCH_CAPACITY * 2 + 37


def _parallel_task(warc_path: str) -> Iterator[Article]:
    yield Article(
        html=HTML(
            requested_url=f"https://example.com/{warc_path}",
            responded_url=f"https://example.com/{warc_path}",
            content="<html></html>",
            crawl_date=datetime(2020, 1, 1),
            source_info=SourceInfo(publisher="test_pub"),
        )
    )


def _reporting_task(warc_path: str) -> Iterator[Article]:
    """Report the worker's own logging setup, through the worker's own logger."""
    from fundus.logging import get_handlers
    from fundus.scraping.crawler.ccnews import logger

    logger.error(f"handlers={[handler.name for handler in get_handlers()]}")
    return iter(())


def _debug_task(warc_path: str) -> Iterator[Article]:
    """Log below the library level, through a module the parent raised to DEBUG."""
    from fundus.scraping.pipeline.source.ccnews import logger

    logger.debug("scoped debug from the worker")
    return iter(())


def _chatty_task(warc_path: str) -> Iterator[Article]:
    """Log more records than fit in one batch, so several have to cross together."""
    from fundus.scraping.crawler.ccnews import logger

    for index in range(_CHATTER):
        logger.debug("chatter %d", index)
    return iter(())


@contextmanager
def capture_fundus_logs() -> Iterator[io.StringIO]:
    """Capture everything the Fundus loggers emit in this process."""
    buffer = io.StringIO()
    handler = logging.StreamHandler(buffer)
    handler.set_name("integration-probe")
    add_handler(handler)
    try:
        yield buffer
    finally:
        remove_handler("integration-probe")


@pytest.mark.integration
class TestCrawlerThreadedIntegration:
    def test_articles_flow_through_thread_pool(self, publisher_group_with_news_map):
        fake_articles = [make_article(html=make_html(requested_url=f"https://example.com/{i}")) for i in range(3)]
        crawler = Crawler(publisher_group_with_news_map, threading=True, ignore_robots=True)

        def mock_run(self, *args, **kwargs):
            yield from fake_articles

        with patch.object(Pipeline, "run", mock_run):
            result = list(crawler.crawl(max_articles=3, only_complete=False))

        assert len(result) == 3


@pytest.mark.integration
class TestCCNewsCrawlerIntegration:
    def test_single_process_full_pipeline(self, publisher_group_with_news_map):
        crawler = CCNewsCrawler(
            publisher_group_with_news_map,
            start=datetime(2020, 1, 1),
            end=datetime(2021, 1, 1),
            processes=0,
        )
        fake = make_article(html=make_html(requested_url="https://example.com/1"))

        with patch.object(crawler, "_get_warc_paths", return_value=["fake.warc.gz"]), patch(
            "fundus.scraping.crawler.ccnews.Pipeline"
        ) as MockPipeline:
            MockPipeline.return_value.run.return_value = iter([fake])
            result = list(crawler.crawl(max_articles=1, only_complete=False))

        assert len(result) == 1

    def test_parallel_process_articles_flow_through_queue(self, publisher_group_with_news_map, main_thread_context):
        crawler = CCNewsCrawler(
            publisher_group_with_news_map,
            start=datetime(2020, 1, 1),
            end=datetime(2021, 1, 1),
            processes=1,
        )
        # patch random_sleep in the main process so no sleep is added to the serialized task
        with patch("fundus.scraping.crawler.ccnews.random_sleep", side_effect=lambda f, _: f):
            result = list(crawler._parallel_crawl(("path1", "path2"), _parallel_task))

        assert len(result) == 2

    def test_worker_records_reach_the_main_process(self, publisher_group_with_news_map, main_thread_context):
        # Only a real pool shows this: that the initializer reaches the worker at all, and
        # that it leaves the worker logging through the queue rather than on its own.
        crawler = CCNewsCrawler(
            publisher_group_with_news_map,
            start=datetime(2020, 1, 1),
            end=datetime(2021, 1, 1),
            processes=1,
        )

        with capture_fundus_logs() as captured, patch(
            "fundus.scraping.crawler.ccnews.random_sleep", side_effect=lambda f, _: f
        ):
            list(crawler._parallel_crawl(("path1",), _reporting_task))

        assert "handlers=['fundus-queue']" in captured.getvalue()

    def test_every_record_a_worker_batches_reaches_the_main_process(
        self, publisher_group_with_news_map, main_thread_context
    ):
        # More records than fit in one batch, so the run covers both halves of the deal:
        # batches sent when they fill up, and the remainder sent when the work ends. The
        # remainder is the part that would otherwise go down with the terminated worker.
        crawler = CCNewsCrawler(
            publisher_group_with_news_map,
            start=datetime(2020, 1, 1),
            end=datetime(2021, 1, 1),
            processes=1,
        )
        set_log_level(logging.DEBUG)
        try:
            with capture_fundus_logs() as captured, patch(
                "fundus.scraping.crawler.ccnews.random_sleep", side_effect=lambda f, _: f
            ):
                list(crawler._parallel_crawl(("path1",), _chatty_task))
        finally:
            set_log_level(logging.ERROR)

        assert captured.getvalue().count("chatter ") == _CHATTER

    def test_a_scoped_level_reaches_the_worker(self, publisher_group_with_news_map, main_thread_context):
        # Under spawn the worker starts at the default level, so a module raised to DEBUG
        # here is only heard from a worker if that level travels with the initializer.
        crawler = CCNewsCrawler(
            publisher_group_with_news_map,
            start=datetime(2020, 1, 1),
            end=datetime(2021, 1, 1),
            processes=1,
        )
        set_log_level(logging.DEBUG, logger="fundus.scraping.pipeline.source.ccnews")
        try:
            with capture_fundus_logs() as captured, patch(
                "fundus.scraping.crawler.ccnews.random_sleep", side_effect=lambda f, _: f
            ):
                list(crawler._parallel_crawl(("path1",), _debug_task))
        finally:
            set_log_level(logging.NOTSET, logger="fundus.scraping.pipeline.source.ccnews")

        assert "scoped debug from the worker" in captured.getvalue()


@pytest.mark.integration
class TestTimeoutIntegration:
    def test_crawl_terminates_on_timeout(self, publisher_group_with_news_map):
        timeout = 0.3

        class TimeoutCrawler(FakeCrawler):
            def _on_timeout(self) -> None:
                _interrupt_handler()

            def _build_article_iterator(self, *args, **kwargs) -> Iterator[Article]:
                yield make_article(html=make_html(requested_url="https://example.com/1"))
                while True:
                    time.sleep(0.001)  # short sleeps so Windows processes the pending KeyboardInterrupt

        crawler = TimeoutCrawler(publisher_group_with_news_map)
        start = time.time()
        result = list(crawler.crawl(timeout=timeout, only_complete=False))
        elapsed = time.time() - start

        assert len(result) == 1
        assert elapsed < timeout + 0.3
