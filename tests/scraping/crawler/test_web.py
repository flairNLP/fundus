import pytest

from fundus import Crawler, NewsMap, RSSFeed
from fundus.scraping.pipeline.source.web import WebSource
from fundus.utils.events import __EVENTS__
from tests.fixtures.builders import make_publisher


class TestPipeline:
    def test_crawler_with_empty_collection(self, group_with_empty_publisher_subgroup):
        with pytest.raises(ValueError):
            Crawler(group_with_empty_publisher_subgroup)

        with pytest.raises(ValueError):
            Crawler(*group_with_empty_publisher_subgroup)

    def test_crawler_with_collection(self, group_with_valid_publisher_subgroup):
        crawler = Crawler(*group_with_valid_publisher_subgroup)
        assert len(crawler.publishers) == 1

    def test_crawler_with_two_collections(
        self,
        group_with_valid_publisher_subgroup,
        group_with_empty_publisher_subgroup,
        group_with_two_valid_publisher_subgroups,
    ):
        crawler = Crawler(group_with_empty_publisher_subgroup, group_with_valid_publisher_subgroup)
        assert len(crawler.publishers) == 1

        crawler = Crawler(group_with_valid_publisher_subgroup, group_with_valid_publisher_subgroup)
        assert len(crawler.publishers) == 1

        crawler = Crawler(group_with_two_valid_publisher_subgroups)
        assert len(crawler.publishers) == 2

        crawler = Crawler(group_with_valid_publisher_subgroup, group_with_two_valid_publisher_subgroups)
        assert len(crawler.publishers) == 3

    def test_crawler_with_publisher_enum(self, publisher_group_with_rss_feeds, publisher_group_with_news_map):
        crawler = Crawler(publisher_group_with_rss_feeds, publisher_group_with_news_map)
        assert len(crawler.publishers) == 2

        crawler = Crawler(publisher_group_with_rss_feeds, publisher_group_with_news_map, restrict_sources_to=[RSSFeed])
        assert len(crawler.publishers) == 2

        crawler = Crawler(publisher_group_with_rss_feeds, publisher_group_with_news_map, restrict_sources_to=[NewsMap])
        assert len(crawler.publishers) == 2

    def test_consecutive_calls_to_crawl(self, group_with_valid_publisher_subgroup):
        crawler = Crawler(group_with_valid_publisher_subgroup)
        next(crawler.crawl(max_articles=0), None)
        next(crawler.crawl(max_articles=0), None)


class TestImpersonate:
    def test_crawler_default_impersonate_false(self, group_with_valid_publisher_subgroup):
        crawler = Crawler(group_with_valid_publisher_subgroup)
        assert crawler.impersonate is False

    def test_crawler_stores_impersonate_flag(self, group_with_valid_publisher_subgroup):
        crawler = Crawler(group_with_valid_publisher_subgroup, impersonate=True)
        assert crawler.impersonate is True

    def test_websource_disabled_drops_publisher_profile(self):
        publisher = make_publisher(impersonate="chrome")
        source = WebSource(url_source=[], publisher=publisher, impersonate=False)
        assert source._impersonate_profile is None

    def test_websource_enabled_uses_publisher_profile(self):
        publisher = make_publisher(impersonate="chrome")
        source = WebSource(url_source=[], publisher=publisher, impersonate=True)
        assert source._impersonate_profile == publisher.impersonate


class TestCrawlerResolveDelay:
    def test_none_returns_none(self):
        assert Crawler._resolve_delay(None) is None

    def test_float_returns_constant_callable(self):
        delay = Crawler._resolve_delay(1.5)
        assert callable(delay)
        assert delay() == 1.5

    def test_int_returns_constant_callable(self):
        delay = Crawler._resolve_delay(2)
        assert callable(delay)
        assert delay() == 2

    def test_callable_returned_as_is(self):
        def fn() -> float:
            return 0.5

        assert Crawler._resolve_delay(fn) is fn

    def test_invalid_type_raises(self):
        with pytest.raises(TypeError):
            Crawler._resolve_delay("1.0")  # type: ignore[arg-type]


class TestCrawlerBuildPipelines:
    @pytest.fixture(autouse=True)
    def _main_context(self):
        # _build_pipelines constructs WebSource, which looks up __EVENTS__.get("stop")
        # at construction time. Production always calls this inside main_context
        # (threading mode adds a publisher context on top); mirror that here.
        with __EVENTS__.main_context("test"):
            yield

    def test_returns_one_pipeline_per_source(self, publisher_group_with_news_map):
        crawler = Crawler(publisher_group_with_news_map, ignore_robots=True)
        pipelines = crawler._build_pipelines(crawler.publishers[0])
        assert len(pipelines) == 1

    def test_restrict_sources_excludes_non_matching_type(self, publisher_group_with_rss_feeds):
        crawler = Crawler(publisher_group_with_rss_feeds, ignore_robots=True, restrict_sources_to=[NewsMap])
        pipelines = crawler._build_pipelines(crawler.publishers[0])
        assert pipelines == []

    def test_no_restriction_includes_all_sources(self, publisher_group_with_rss_feeds):
        crawler = Crawler(publisher_group_with_rss_feeds, ignore_robots=True)
        pipelines = crawler._build_pipelines(crawler.publishers[0])
        assert len(pipelines) == 1
