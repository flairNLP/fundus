import pytest

from fundus import Crawler, NewsMap, RSSFeed


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
