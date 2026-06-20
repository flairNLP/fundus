import pytest

from fundus import Crawler, NewsMap, RSSFeed
from fundus.publishers.base_objects import Publisher
from fundus.scraping.html import WebSource


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

    def test_websource_disabled_drops_publisher_profile(self, parser_proxy_with_version):
        publisher = Publisher(
            name="impersonating",
            domain="https://test.com/",
            sources=[RSSFeed("https://test.com/feed")],
            parser=parser_proxy_with_version,
            impersonate="chrome",
        )
        source = WebSource(
            url_source=publisher.source_mapping[RSSFeed][0],
            publisher=publisher,
            impersonate=False,
        )
        assert source._impersonate_profile is None

    def test_websource_enabled_uses_publisher_profile(self, parser_proxy_with_version):
        publisher = Publisher(
            name="impersonating",
            domain="https://test.com/",
            sources=[RSSFeed("https://test.com/feed")],
            parser=parser_proxy_with_version,
            impersonate="chrome",
        )
        source = WebSource(
            url_source=publisher.source_mapping[RSSFeed][0],
            publisher=publisher,
            impersonate=True,
        )
        assert source._impersonate_profile == publisher.impersonate
