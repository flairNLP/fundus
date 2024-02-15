import pytest

from fundus import NewsMap, RSSFeed, Sitemap
from fundus.publishers.base_objects import PublisherCollectionMeta, PublisherEnum


class TestCollection:
    def test_iter_empty_collection(self, empty_collection):
        assert list(empty_collection) == []

    def test_iter_collection_with_empty_publisher_enum(self, collection_with_empty_publisher_enum):
        assert list(collection_with_empty_publisher_enum) == []

    def test_iter_collection_with_publisher_enum(self, collection_with_valid_publisher_enum):
        assert list(collection_with_valid_publisher_enum) == [collection_with_valid_publisher_enum.pub.value]

    def test_publisher_enum_with_wrong_enum_value(self):
        with pytest.raises(ValueError):

            class PublisherEnumWithWrongValue(PublisherEnum):
                value = "Enum"

    def test_duplicate_publisher_names_in_same_collection(self, publisher_enum_with_news_map):
        with pytest.raises(AttributeError):

            class Test(metaclass=PublisherCollectionMeta):
                a = publisher_enum_with_news_map
                b = publisher_enum_with_news_map

    def test_supports(self, publisher_enum_with_news_map):
        assert publisher_enum_with_news_map.value.supports([NewsMap])
        assert not publisher_enum_with_news_map.value.supports([Sitemap])
        assert not publisher_enum_with_news_map.value.supports([RSSFeed])
        with pytest.raises(ValueError):
            publisher_enum_with_news_map.value.supports("")

        with pytest.raises(TypeError):
            publisher_enum_with_news_map.value.supports([""])

    def test_search(self, publisher_enum_with_news_map, proxy_with_two_versions_and_different_attrs):
        parser_proxy = proxy_with_two_versions_and_different_attrs()

        # monkey pathing publisher enums parser
        publisher_enum_with_news_map.value.parser = parser_proxy

        later, earlier = parser_proxy.attribute_mapping.values()

        assert len(publisher_enum_with_news_map.search(later.names, [NewsMap])) == 1
        assert len(publisher_enum_with_news_map.search(later.names, [RSSFeed, Sitemap])) == 0
        assert len(publisher_enum_with_news_map.search(later.names, [NewsMap, RSSFeed])) == 0

        # check that only latest version is supported with search
        assert len(publisher_enum_with_news_map.search(later.names)) == 1
        assert len(publisher_enum_with_news_map.search(earlier.names)) == 0

        with pytest.raises(ValueError):
            publisher_enum_with_news_map.search()

        with pytest.raises(ValueError):
            publisher_enum_with_news_map.search([])

        with pytest.raises(ValueError):
            publisher_enum_with_news_map.search([], [])
