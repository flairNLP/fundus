import pytest

from fundus import Crawler, NewsMap, RSSFeed


class TestPipeline:
    def test_crawler_with_empty_collection(self, collection_with_empty_publisher_enum):
        crawler = Crawler(collection_with_empty_publisher_enum)
        assert crawler.scrapers == tuple()
        assert next(crawler.crawl(), None) is None

        with pytest.raises(ValueError):
            Crawler(*collection_with_empty_publisher_enum)

    def test_crawler_with_collection(self, collection_with_validate_publisher_enum):
        crawler = Crawler(*collection_with_validate_publisher_enum)
        publisher = collection_with_validate_publisher_enum.pub.value
        print(crawler.scrapers)
        assert len(crawler.scrapers) == 1
        assert len(crawler.scrapers[0].sources) == len(
            list(value for value in publisher.source_mapping.values() if value)
        )

    def test_crawler_with_publisher_enum(self, publisher_enum_with_rss_feeds, publisher_enum_with_news_map):
        crawler = Crawler(publisher_enum_with_rss_feeds, publisher_enum_with_news_map)
        assert len(crawler.scrapers) == 2

        crawler = Crawler(publisher_enum_with_rss_feeds, publisher_enum_with_news_map, restrict_sources_to=[RSSFeed])
        assert len(crawler.scrapers) == 1
        assert crawler.scrapers[0].sources == publisher_enum_with_rss_feeds.value.source_mapping[RSSFeed]

        crawler = Crawler(publisher_enum_with_rss_feeds, publisher_enum_with_news_map, restrict_sources_to=[NewsMap])
        assert len(crawler.scrapers) == 1
        assert crawler.scrapers[0].sources == publisher_enum_with_news_map.value.source_mapping[NewsMap]
