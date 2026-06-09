from __future__ import annotations

import time
from datetime import datetime
from typing import Iterator
from unittest.mock import patch

import pytest

from fundus import Crawler
from fundus.scraping.article import Article
from fundus.scraping.crawler import CCNewsCrawler
from fundus.scraping.html import HTML, SourceInfo
from fundus.scraping.pipeline import Pipeline
from fundus.utils.timeout import _interrupt_handler
from tests.fixtures.builders import make_article, make_html
from tests.fixtures.fakes import FakeCrawler


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
