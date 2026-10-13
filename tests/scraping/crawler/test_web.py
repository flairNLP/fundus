import threading

import pytest

from fundus import Crawler, NewsMap, Requires, RSSFeed, Sitemap
from fundus.scraping.crawler import supports_attributes
from fundus.scraping.delay import RobotsCrawlDelay
from fundus.scraping.pipeline.source.interleaved import InterleavedSource
from fundus.scraping.pipeline.source.web import WebSource
from fundus.utils.events import __EVENTS__
from tests.fixtures.builders import make_publisher, mock_robots, stub_publisher


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


class TestSupportsAttributes:
    def test_without_a_requires_filter_anything_is_supported(self, proxy_with_two_versions_and_different_attrs):
        assert supports_attributes(None, proxy_with_two_versions_and_different_attrs()) is True

    def test_a_version_covering_the_requirements_supports_them(self, proxy_with_two_versions_and_different_attrs):
        proxy = proxy_with_two_versions_and_different_attrs()
        assert supports_attributes(Requires("title"), proxy) is True
        assert supports_attributes(Requires("another_title"), proxy) is True

    def test_requirements_split_between_versions_are_not_supported(self, proxy_with_two_versions_and_different_attrs):
        # 'title' comes from one version and 'another_title' from the other, so no article, which
        # is parsed by a single version, could ever carry both.
        proxy = proxy_with_two_versions_and_different_attrs()
        assert supports_attributes(Requires("title", "another_title"), proxy) is False

    def test_without_a_version_nothing_is_supported(self):
        assert supports_attributes(Requires("title"), []) is False


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

    def test_returns_one_pipeline_per_batch_in_crawl_order(self):
        publisher = make_publisher(
            sources=[
                Sitemap("https://test.com/sitemap"),
                RSSFeed("https://test.com/one", interleave=True),
                NewsMap("https://test.com/news"),
                RSSFeed("https://test.com/two", interleave=True),
            ]
        )
        crawler = Crawler(publisher, ignore_robots=True)
        pipelines = crawler._build_pipelines(crawler.publishers[0])

        assert all(isinstance(pipeline.source, InterleavedSource) for pipeline in pipelines)
        assert [[source.url_source.url for source in pipeline.source.sources] for pipeline in pipelines] == [
            ["https://test.com/one", "https://test.com/two"],
            ["https://test.com/news"],
            ["https://test.com/sitemap"],
        ]

    def test_all_sources_of_a_publisher_share_one_pacer(self):
        publisher = make_publisher(
            sources=[RSSFeed("https://test.com/one", interleave=True), RSSFeed("https://test.com/two", interleave=True)]
            + [Sitemap("https://test.com/sitemap")]
        )
        crawler = Crawler(publisher, ignore_robots=True)
        pipelines = crawler._build_pipelines(crawler.publishers[0])

        pacers = {id(source.pacer) for pipeline in pipelines for source in pipeline.source.sources}
        assert len(pacers) == 1
        assert None not in {source.pacer for pipeline in pipelines for source in pipeline.source.sources}

    def test_restrict_sources_excludes_non_matching_type(self, publisher_group_with_rss_feeds):
        crawler = Crawler(publisher_group_with_rss_feeds, ignore_robots=True, restrict_sources_to=[NewsMap])
        pipelines = crawler._build_pipelines(crawler.publishers[0])
        assert pipelines == []

    def test_no_restriction_includes_all_sources(self, publisher_group_with_rss_feeds):
        crawler = Crawler(publisher_group_with_rss_feeds, ignore_robots=True)
        pipelines = crawler._build_pipelines(crawler.publishers[0])
        assert len(pipelines) == 1


class TestCrawlerPublisherPacer:
    def test_robots_crawl_delay_overrides_the_crawlers_delay(self):
        crawler = Crawler(make_publisher(), delay=2.0)
        pacer = crawler._publisher_pacer(stub_publisher(robots=mock_robots(crawl_delay=5.0)), threading.Event())
        assert isinstance(pacer.delay, RobotsCrawlDelay)
        assert pacer.delay() == 5.0

    def test_falls_back_to_the_crawlers_delay(self):
        crawler = Crawler(make_publisher(), delay=2.0)
        pacer = crawler._publisher_pacer(stub_publisher(robots=mock_robots(crawl_delay=None)), threading.Event())
        assert pacer.delay is not None
        assert pacer.delay() == 2.0

    @pytest.mark.parametrize("ignore", [{"ignore_robots": True}, {"ignore_crawl_delay": True}])
    def test_ignoring_robots_or_its_crawl_delay_keeps_the_crawlers_delay(self, ignore):
        robots = mock_robots(crawl_delay=5.0)
        crawler = Crawler(make_publisher(), delay=2.0, **ignore)
        pacer = crawler._publisher_pacer(stub_publisher(robots=robots), threading.Event())
        assert pacer.delay is crawler._delay
        robots.crawl_delay.assert_not_called()

    def test_delay_is_interrupted_by_the_stop_event(self):
        stop_event = threading.Event()
        pacer = Crawler(make_publisher())._publisher_pacer(stub_publisher(robots=mock_robots()), stop_event)
        assert pacer.sleep == stop_event.wait
