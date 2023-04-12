from src.fundus import Crawler


class TestPipeline:
    def test_crawler_with_empty_collection(self, collection_with_empty_publisher_enum):
        crawler = Crawler(collection_with_empty_publisher_enum)
        assert crawler.publishers == set()
        assert next(crawler.crawl(), None) is None

    def test_crawler_with_collection(self, collection_with_validate_publisher_enum):
        crawler = Crawler(collection_with_validate_publisher_enum)
        assert crawler.publishers == set(collection_with_validate_publisher_enum)
