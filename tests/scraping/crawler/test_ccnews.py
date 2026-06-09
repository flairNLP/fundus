from __future__ import annotations

import gzip
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from fundus.scraping.crawler import CCNewsCrawler
from fundus.scraping.pipeline.source.ccnews import WarcFileLoadError
from tests.fixtures.builders import make_article, make_html


class TestCCNewsCrawlerInit:
    def test_raises_when_start_equals_end(self, publisher_group_with_news_map):
        date = datetime(2020, 1, 1)
        with pytest.raises(ValueError, match="Start date has to be < end date"):
            CCNewsCrawler(publisher_group_with_news_map, start=date, end=date)

    def test_raises_when_start_after_end(self, publisher_group_with_news_map):
        with pytest.raises(ValueError, match="Start date has to be < end date"):
            CCNewsCrawler(
                publisher_group_with_news_map,
                start=datetime(2021, 1, 1),
                end=datetime(2020, 1, 1),
            )

    def test_raises_when_start_before_minimum(self, publisher_group_with_news_map):
        with pytest.raises(ValueError, match="2016/08/01"):
            CCNewsCrawler(publisher_group_with_news_map, start=datetime(2016, 7, 31))

    def test_raises_when_end_in_future(self, publisher_group_with_news_map):
        with pytest.raises(ValueError, match="future"):
            CCNewsCrawler(publisher_group_with_news_map, end=datetime(2099, 1, 1))

    def test_default_end_is_evaluated_at_construction_time(self, publisher_group_with_news_map):
        crawler = CCNewsCrawler(publisher_group_with_news_map, start=datetime(2020, 1, 1))
        assert crawler.end <= datetime.now()


class TestFetchArticles:
    def test_retries_on_warc_file_load_error(self, publisher_group_with_news_map):
        crawler = CCNewsCrawler(
            publisher_group_with_news_map,
            start=datetime(2020, 1, 1),
            end=datetime(2021, 1, 1),
            retries=2,
        )
        publishers = tuple(crawler.publishers)

        with patch("fundus.scraping.crawler.ccnews.Pipeline") as MockPipeline, patch("time.sleep"):
            MockPipeline.return_value.run.side_effect = WarcFileLoadError("test")
            list(crawler._fetch_articles("fake/path.warc.gz", publishers, False))

        assert MockPipeline.call_count == 3  # initial attempt + 2 retries

    def test_stops_immediately_on_success(self, publisher_group_with_news_map):
        crawler = CCNewsCrawler(
            publisher_group_with_news_map,
            start=datetime(2020, 1, 1),
            end=datetime(2021, 1, 1),
            retries=3,
        )
        publishers = tuple(crawler.publishers)
        fake = make_article(html=make_html(requested_url="https://example.com/1"))

        with patch("fundus.scraping.crawler.ccnews.Pipeline") as MockPipeline:
            MockPipeline.return_value.run.return_value = iter([fake])
            result = list(crawler._fetch_articles("fake/path.warc.gz", publishers, False))

        assert result == [fake]
        assert MockPipeline.call_count == 1


class TestGetWarcPaths:
    def test_filters_paths_by_date_range(self, publisher_group_with_news_map):
        # single month so requests.Session.get is called exactly once
        crawler = CCNewsCrawler(
            publisher_group_with_news_map,
            start=datetime(2020, 6, 1),
            end=datetime(2020, 6, 30),
            processes=0,
        )
        paths = [
            "crawl-data/CC-NEWS/2020/06/CC-NEWS-20200615000000-00001.warc.gz",  # in range
            "crawl-data/CC-NEWS/2020/05/CC-NEWS-20200531000000-00001.warc.gz",  # before start
            "crawl-data/CC-NEWS/2020/07/CC-NEWS-20200701000000-00001.warc.gz",  # after end
        ]
        mock_response = MagicMock()
        mock_response.content = gzip.compress("\n".join(paths).encode())

        with patch("requests.Session.get", return_value=mock_response):
            result = crawler._get_warc_paths()

        assert len(result) == 1
        assert result[0] == f"{crawler.server_address}{paths[0]}"

    def test_results_sorted_newest_first(self, publisher_group_with_news_map):
        crawler = CCNewsCrawler(
            publisher_group_with_news_map,
            start=datetime(2020, 6, 1),
            end=datetime(2020, 6, 30),
            processes=0,
        )
        paths = [
            "crawl-data/CC-NEWS/2020/06/CC-NEWS-20200610000000-00001.warc.gz",
            "crawl-data/CC-NEWS/2020/06/CC-NEWS-20200620000000-00001.warc.gz",
            "crawl-data/CC-NEWS/2020/06/CC-NEWS-20200601000000-00001.warc.gz",
        ]
        mock_response = MagicMock()
        mock_response.content = gzip.compress("\n".join(paths).encode())

        with patch("requests.Session.get", return_value=mock_response):
            result = crawler._get_warc_paths()

        assert "20200620" in result[0]
        assert "20200601" in result[-1]


class TestDispatch:
    def test_single_crawl_when_processes_zero(self, publisher_group_with_news_map):
        crawler = CCNewsCrawler(
            publisher_group_with_news_map,
            start=datetime(2020, 1, 1),
            end=datetime(2021, 1, 1),
            processes=0,
        )
        with patch.object(crawler, "_get_warc_paths", return_value=["path1"]), patch.object(
            crawler, "_single_crawl"
        ) as mock_single, patch("fundus.scraping.crawler.ccnews.get_proxy_tqdm"):
            mock_single.return_value = iter([])
            list(crawler._build_article_iterator(tuple(crawler.publishers), False, None, None, None))

        mock_single.assert_called_once()

    def test_parallel_crawl_when_processes_nonzero(self, publisher_group_with_news_map):
        crawler = CCNewsCrawler(
            publisher_group_with_news_map,
            start=datetime(2020, 1, 1),
            end=datetime(2021, 1, 1),
            processes=1,
        )
        with patch.object(crawler, "_get_warc_paths", return_value=["path1"]), patch.object(
            crawler, "_parallel_crawl"
        ) as mock_parallel, patch("fundus.scraping.crawler.ccnews.get_proxy_tqdm"):
            mock_parallel.return_value = iter([])
            list(crawler._build_article_iterator(tuple(crawler.publishers), False, None, None, None))

        mock_parallel.assert_called_once()
