import pytest

from src.fundus.parser import BaseParser
from src.fundus.publishers.base_objects import PublisherEnum, PublisherSpec


class TestCollection:
    def test_iter_empty_collection(self, empty_collection):
        assert list(empty_collection) == []

    def test_iter_collection_with_empty_publisher_enum(self, collection_with_empty_publisher_enum):
        assert list(collection_with_empty_publisher_enum) == []

    def test_iter_collection_with_publisher_enum(self, collection_with_validate_publisher_enum):
        assert list(collection_with_validate_publisher_enum) == [collection_with_validate_publisher_enum.pub.value]

    def test_publisher_enum_with_wrong_enum_value(self):
        with pytest.raises(ValueError):

            class PublisherEnumWithWrongValue(PublisherEnum):
                value = "Enum"

    def test_publisher_enum_with_publisher_spec_without_source(self):
        with pytest.raises(ValueError):

            class EmptyParser(BaseParser):
                pass

            class PublisherEnumWithWrongValueSpec(PublisherEnum):
                value = PublisherSpec(name="test_pub", domain="https//:test.com/", parser=EmptyParser)

    def test_supports(self, publisher_enum_with_news_map):
        assert publisher_enum_with_news_map.value.supports("news")
        assert not publisher_enum_with_news_map.value.supports("sitemap")
        assert not publisher_enum_with_news_map.value.supports("rss")
        with pytest.raises(ValueError):
            publisher_enum_with_news_map.value.supports("")

    def test_search(self, publisher_enum_with_news_map, parser_with_attr_title):
        publisher_enum_with_news_map.value.parser = parser_with_attr_title

        assert (attrs := publisher_enum_with_news_map.value.parser.attributes().names)
        assert attrs == ["title"]
        assert len(publisher_enum_with_news_map.search(attrs)) == 1
        assert len(publisher_enum_with_news_map.search(["this_is_a_test"])) == 0

        with pytest.raises(AssertionError):
            publisher_enum_with_news_map.search([])
            publisher_enum_with_news_map.search()
