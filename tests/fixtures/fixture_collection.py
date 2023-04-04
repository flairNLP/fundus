import pytest

from src.library.collection import CollectionMeta
from src.library.collection.base_objects import PublisherEnum, PublisherSpec


@pytest.fixture
def empty_collection():
    class EmptyCollection(metaclass=CollectionMeta):
        pass

    return EmptyCollection


@pytest.fixture
def empty_publisher_enum():
    class EmptyPublisherEnum(PublisherEnum):
        pass

    return EmptyPublisherEnum


@pytest.fixture
def collection_with_empty_publisher_enum(empty_publisher_enum):
    class CollectionWithEmptyPublisherEnum(metaclass=CollectionMeta):
        empty = empty_publisher_enum

    return CollectionWithEmptyPublisherEnum


@pytest.fixture
def publisher_enum_with_news_map(empty_parser):
    class PubEnum(PublisherEnum):
        value = PublisherSpec(
            name="test_pub", domain="https//:test.com/", news_map="test_news_map", parser=empty_parser
        )

    return PubEnum


@pytest.fixture
def publisher_enum_with_rss_feeds(empty_parser):
    class PubEnum(PublisherEnum):
        value = PublisherSpec(name="test_pub", domain="https//:test.com/", rss_feeds=["test_feed"], parser=empty_parser)

    return PubEnum


@pytest.fixture
def publisher_enum_with_sitemaps(empty_parser):
    class PubEnum(PublisherEnum):
        value = PublisherSpec(
            name="test_pub", domain="https//:test.com/", sitemaps=["test_sitemap"], parser=empty_parser
        )

    return PubEnum


@pytest.fixture
def collection_with_validate_publisher_enum(publisher_enum_with_news_map):
    class CollectionWithValidatePublisherEnum(metaclass=CollectionMeta):
        pub = publisher_enum_with_news_map

    return CollectionWithValidatePublisherEnum
