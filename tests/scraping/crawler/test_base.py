from __future__ import annotations

import json

from fundus.scraping.crawler.base import CrawlerBase, _CrawlState
from fundus.scraping.filter import Requires, RequiresAll
from tests.fixtures.builders import make_article, make_html
from tests.fixtures.fakes import FakeCrawler


class TestCrawlState:
    def test_accept_new_url_returns_true(self):
        state = _CrawlState(only_unique=True, track_articles=False)
        article = make_article(html=make_html(requested_url="https://example.com/1", publisher="pub"))
        assert state.accept(article) is True

    def test_accept_duplicate_returns_false(self):
        state = _CrawlState(only_unique=True, track_articles=False)
        article = make_article(html=make_html(requested_url="https://example.com/1", publisher="pub"))
        state.accept(article)
        assert state.accept(article) is False

    def test_allows_duplicate_when_not_unique(self):
        state = _CrawlState(only_unique=False, track_articles=False)
        article = make_article(html=make_html(requested_url="https://example.com/1", publisher="pub"))
        assert state.accept(article) is True
        assert state.accept(article) is True

    def test_counts_per_publisher_and_total(self):
        state = _CrawlState(only_unique=False, track_articles=False)
        state.accept(make_article(html=make_html(requested_url="https://example.com/1", publisher="pub_a")))
        state.accept(make_article(html=make_html(requested_url="https://example.com/2", publisher="pub_a")))
        state.accept(make_article(html=make_html(requested_url="https://example.com/3", publisher="pub_b")))
        assert state.total_count == 3
        assert state.article_count["pub_a"] == 2
        assert state.article_count["pub_b"] == 1

    def test_tracks_articles_when_enabled(self):
        state = _CrawlState(only_unique=False, track_articles=True)
        article = make_article(html=make_html(requested_url="https://example.com/1", publisher="pub"))
        state.accept(article)
        assert article in state.crawled_articles["pub"]

    def test_does_not_track_when_disabled(self):
        state = _CrawlState(only_unique=False, track_articles=False)
        state.accept(make_article(html=make_html(requested_url="https://example.com/1", publisher="pub")))
        assert len(state.crawled_articles) == 0


class TestBuildExtractionFilter:
    def test_false_returns_none(self):
        assert CrawlerBase._build_extraction_filter(False) is None

    def test_true_returns_requires_all(self):
        assert isinstance(CrawlerBase._build_extraction_filter(True), RequiresAll)

    def test_filter_passed_through(self):
        f = Requires("title")
        assert CrawlerBase._build_extraction_filter(f) is f


class TestFilterPublishers:
    def test_no_extraction_filter_returns_all_publishers(self, publisher_group_with_news_map):
        crawler = FakeCrawler(publisher_group_with_news_map)
        result = crawler._filter_publishers(extraction_filter=None, language_filter=None)
        assert len(result) == len(crawler.publishers)

    def test_unsupported_attribute_filters_out_publisher(self, publisher_group_with_news_map):
        crawler = FakeCrawler(publisher_group_with_news_map)
        # parser_proxy_with_version has no @attribute methods, so any Requires removes it
        result = crawler._filter_publishers(extraction_filter=Requires("nonexistent_attr_xyz"), language_filter=None)
        assert result == []


class TestCrawl:
    def test_max_articles_zero_yields_nothing(self, publisher_group_with_news_map):
        articles = [make_article(html=make_html(requested_url=f"https://example.com/{i}")) for i in range(5)]
        crawler = FakeCrawler(publisher_group_with_news_map, articles=articles)
        assert list(crawler.crawl(max_articles=0, only_complete=False)) == []

    def test_max_articles_limits_output(self, publisher_group_with_news_map):
        articles = [make_article(html=make_html(requested_url=f"https://example.com/{i}")) for i in range(10)]
        crawler = FakeCrawler(publisher_group_with_news_map, articles=articles)
        assert len(list(crawler.crawl(max_articles=3, only_complete=False))) == 3

    def test_only_unique_deduplicates_by_url(self, publisher_group_with_news_map):
        articles = [make_article(html=make_html(requested_url="https://example.com/same"))] * 3
        crawler = FakeCrawler(publisher_group_with_news_map, articles=articles)
        assert len(list(crawler.crawl(only_complete=False, only_unique=True))) == 1

    def test_not_unique_passes_duplicates(self, publisher_group_with_news_map):
        articles = [make_article(html=make_html(requested_url="https://example.com/same"))] * 3
        crawler = FakeCrawler(publisher_group_with_news_map, articles=articles)
        assert len(list(crawler.crawl(only_complete=False, only_unique=False))) == 3

    def test_max_articles_per_publisher(self, publisher_group_with_news_map):
        articles = [make_article(html=make_html(requested_url=f"https://example.com/{i}")) for i in range(5)]
        crawler = FakeCrawler(publisher_group_with_news_map, articles=articles)
        result = list(crawler.crawl(max_articles_per_publisher=2, only_complete=False))
        assert len(result) == 2

    def test_save_to_file_writes_json(self, publisher_group_with_news_map, tmp_path):
        articles = [make_article(html=make_html(requested_url="https://example.com/1"))]
        crawler = FakeCrawler(publisher_group_with_news_map, articles=articles)
        path = tmp_path / "out.json"
        list(crawler.crawl(only_complete=False, save_to_file=str(path)))
        assert path.exists()
        data = json.loads(path.read_text())
        assert "test_pub" in data
