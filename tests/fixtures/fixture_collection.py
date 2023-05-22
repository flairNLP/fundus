import pytest

from fundus.publishers.base_objects import (
    PublisherCollectionMeta,
    PublisherEnum,
    PublisherSpec,
)


@pytest.fixture
def empty_collection():
    class EmptyCollection(metaclass=PublisherCollectionMeta):
        pass

    return EmptyCollection


@pytest.fixture
def empty_publisher_enum():
    class EmptyPublisherEnum(PublisherEnum):
        pass

    return EmptyPublisherEnum


@pytest.fixture
def collection_with_empty_publisher_enum(empty_publisher_enum):
    class CollectionWithEmptyPublisherEnum(metaclass=PublisherCollectionMeta):
        empty = empty_publisher_enum

    return CollectionWithEmptyPublisherEnum


@pytest.fixture
def publisher_enum_with_news_map(parser_proxy_with_version):
    class PubEnum(PublisherEnum):
        value = PublisherSpec(domain="https//:test.com/", news_map="test_news_map", parser=parser_proxy_with_version)

    return PubEnum


@pytest.fixture
def publisher_enum_with_rss_feeds(parser_proxy_with_version):
    class PubEnum(PublisherEnum):
        value = PublisherSpec(domain="https//:test.com/", rss_feeds=["test_feed"], parser=parser_proxy_with_version)

    return PubEnum


@pytest.fixture
def publisher_enum_with_sitemaps(parser_proxy_with_version):
    class PubEnum(PublisherEnum):
        value = PublisherSpec(domain="https//:test.com/", sitemaps=["test_sitemap"], parser=parser_proxy_with_version)

    return PubEnum


@pytest.fixture
def collection_with_validate_publisher_enum(publisher_enum_with_news_map):
    class CollectionWithValidatePublisherEnum(metaclass=PublisherCollectionMeta):
        pub = publisher_enum_with_news_map

    return CollectionWithValidatePublisherEnum
