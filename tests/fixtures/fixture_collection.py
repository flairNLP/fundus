import pytest

from fundus import NewsMap, RSSFeed, Sitemap
from fundus.publishers.base_objects import Publisher, PublisherGroup


@pytest.fixture
def empty_publisher_group():
    class EmptyPublisherGroup(metaclass=PublisherGroup):
        pass

    return EmptyPublisherGroup


@pytest.fixture
def group_with_empty_publisher_subgroup(empty_publisher_group):
    class GroupWithEmptyPublisherSubgroup(metaclass=PublisherGroup):
        empty = empty_publisher_group

    return GroupWithEmptyPublisherSubgroup


@pytest.fixture
def publisher_group_with_news_map(parser_proxy_with_version):
    class PubGroup(metaclass=PublisherGroup):
        value = Publisher(
            name="test_pub",
            domain="https://test.com/",
            sources=[NewsMap("https://test.com/test_news_map")],
            parser=parser_proxy_with_version,
        )

    return PubGroup


@pytest.fixture
def publisher_group_with_rss_feeds(parser_proxy_with_version):
    class PubGroup(metaclass=PublisherGroup):
        value = Publisher(
            name="test_pub",
            domain="https://test.com/",
            sources=[RSSFeed("https://test.com/test_feed")],
            parser=parser_proxy_with_version,
        )

    return PubGroup


@pytest.fixture
def publisher_group_with_sitemaps(parser_proxy_with_version):
    class PubGroup(metaclass=PublisherGroup):
        value = Publisher(
            name="test_pub",
            domain="https://test.com/",
            sources=[Sitemap("https://test.com/test_sitemap")],
            parser=parser_proxy_with_version,
        )

    return PubGroup


@pytest.fixture
def group_with_valid_publisher_subgroup(publisher_group_with_news_map):
    class CollectionWithValidatePublisherEnum(metaclass=PublisherGroup):
        pub = publisher_group_with_news_map

    return CollectionWithValidatePublisherEnum


@pytest.fixture
def group_with_two_valid_publisher_subgroups(parser_proxy_with_version):
    class PubGroupNews(metaclass=PublisherGroup):
        news = Publisher(
            name="test_pub",
            domain="https://test.com/",
            sources=[NewsMap("https://test.com/test_newsmap")],
            parser=parser_proxy_with_version,
        )

    class PubGroupSitemap(metaclass=PublisherGroup):
        sitemap = Publisher(
            name="test_pub",
            domain="https://test.com/",
            sources=[Sitemap("https://test.com/test_sitemap")],
            parser=parser_proxy_with_version,
        )

    class GroupWithTwoValidatePublisherSubGroups(metaclass=PublisherGroup):
        enum_news = PubGroupNews
        enum_sitemap = PubGroupSitemap

    return GroupWithTwoValidatePublisherSubGroups


@pytest.fixture
def publisher_group_with_languages(parser_proxy_with_version):
    class LangPubGroup(metaclass=PublisherGroup):
        default_language = "en"

        eng = Publisher(
            name="test_pub_eng",
            domain="https://test.com/",
            sources=[NewsMap("https://test.com/test_sitemap")],
            parser=parser_proxy_with_version,
        )

        ger = Publisher(
            name="test_pub_ger",
            domain="https://test.com/",
            sources=[Sitemap("https://test.com/test_sitemap", languages={"de"})],
            parser=parser_proxy_with_version,
        )

        mixed = Publisher(
            name="test_pub_mixed",
            domain="https://test.com/",
            sources=[
                RSSFeed("https://test.com/test_feed", languages={"es", "pl"}),
                NewsMap("https://test.com/test_newsmap", languages={"es"}),
                Sitemap("https://test.com/test_sitemap", languages={"ind"}),
            ],
            parser=parser_proxy_with_version,
        )

    return LangPubGroup
