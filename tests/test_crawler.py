import pytest

from fundus import Crawler, NewsMap, RSSFeed


class TestPipeline:
    def test_crawler_with_empty_collection(self, collection_with_empty_publisher_enum):
        crawler = Crawler(collection_with_empty_publisher_enum)
        assert crawler.publishers == list()
        assert next(crawler.crawl(), None) is None

        with pytest.raises(ValueError):
            Crawler(*collection_with_empty_publisher_enum)

    def test_crawler_with_collection(self, collection_with_valid_publisher_enum):
        crawler = Crawler(*collection_with_valid_publisher_enum)
        publisher = collection_with_valid_publisher_enum.pub.value
        assert len(crawler.publishers) == 1

    def test_crawler_with_two_collections(
        self,
        collection_with_valid_publisher_enum,
        collection_with_empty_publisher_enum,
        collection_with_two_valid_publisher_enum,
    ):
        crawler = Crawler(collection_with_empty_publisher_enum, collection_with_valid_publisher_enum)
        assert len(crawler.publishers) == 1

        crawler = Crawler(collection_with_valid_publisher_enum, collection_with_valid_publisher_enum)
        assert len(crawler.publishers) == 1

        crawler = Crawler(collection_with_two_valid_publisher_enum)
        assert len(crawler.publishers) == 2

        crawler = Crawler(collection_with_valid_publisher_enum, collection_with_two_valid_publisher_enum)
        assert len(crawler.publishers) == 3

    def test_crawler_with_publisher_enum(self, publisher_enum_with_rss_feeds, publisher_enum_with_news_map):
        crawler = Crawler(publisher_enum_with_rss_feeds, publisher_enum_with_news_map)
        assert len(crawler.publishers) == 2

        crawler = Crawler(publisher_enum_with_rss_feeds, publisher_enum_with_news_map, restrict_sources_to=[RSSFeed])
        assert len(crawler.publishers) == 2

        crawler = Crawler(publisher_enum_with_rss_feeds, publisher_enum_with_news_map, restrict_sources_to=[NewsMap])
        assert len(crawler.publishers) == 2

    def test_consecutive_calls_to_crawl(self, collection_with_valid_publisher_enum):
        crawler = Crawler(collection_with_valid_publisher_enum)
        next(crawler.crawl(max_articles=0), None)
        next(crawler.crawl(max_articles=0), None)
