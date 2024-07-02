import pytest

from fundus import NewsMap, RSSFeed, Sitemap


class TestCollection:
    def test_len(
        self,
        empty_publisher_group,
        group_with_empty_publisher_subgroup,
        group_with_valid_publisher_subgroup,
        group_with_two_valid_publisher_subgroups,
    ):
        assert len(empty_publisher_group) == 0
        assert len(group_with_empty_publisher_subgroup) == 0
        assert len(group_with_valid_publisher_subgroup) == 1
        assert len(group_with_two_valid_publisher_subgroups) == 2

    def test_iter_empty_group(self, empty_publisher_group):
        assert list(empty_publisher_group) == []

    def test_iter_group_with_empty_publisher_subgroup(self, group_with_empty_publisher_subgroup):
        assert list(group_with_empty_publisher_subgroup) == []

    def test_iter_group_with_publisher_subgroup(self, group_with_valid_publisher_subgroup):
        assert list(group_with_valid_publisher_subgroup) == [group_with_valid_publisher_subgroup.pub.value]

    def test_supports(self, publisher_group_with_news_map):
        assert publisher_group_with_news_map.value.supports([NewsMap])
        assert not publisher_group_with_news_map.value.supports([Sitemap])
        assert not publisher_group_with_news_map.value.supports([RSSFeed])
        with pytest.raises(ValueError):
            publisher_group_with_news_map.value.supports("")

        with pytest.raises(TypeError):
            publisher_group_with_news_map.value.supports([""])

    def test_search(self, publisher_group_with_news_map, proxy_with_two_versions_and_different_attrs):
        parser_proxy = proxy_with_two_versions_and_different_attrs()

        # monkey pathing publisher enums parser
        publisher_group_with_news_map.value.parser = parser_proxy

        later, earlier = parser_proxy.attribute_mapping.values()

        assert len(publisher_group_with_news_map.search(later.names, [NewsMap])) == 1
        assert len(publisher_group_with_news_map.search(later.names, [RSSFeed, Sitemap])) == 0
        assert len(publisher_group_with_news_map.search(later.names, [NewsMap, RSSFeed])) == 0

        # check that only latest version is supported with search
        assert len(publisher_group_with_news_map.search(later.names)) == 1
        assert len(publisher_group_with_news_map.search(earlier.names)) == 0

        with pytest.raises(ValueError):
            publisher_group_with_news_map.search()

        with pytest.raises(ValueError):
            publisher_group_with_news_map.search([])

        with pytest.raises(ValueError):
            publisher_group_with_news_map.search([], [])

    def test_publisher_group_with_subgroup_string_representation(self, group_with_two_valid_publisher_subgroups):
        representation = str(group_with_two_valid_publisher_subgroups)
        assertion = (
            "<GroupWithTwoValidatePublisherSubGroups: 2>"
            "\n\t<PubGroupNews: 1>"
            "\n\t\ttest_pub"
            "\n\t<PubGroupSitemap: 1>"
            "\n\t\ttest_pub"
        )
        assert representation == assertion

    def test_publisher_group_with_publisher_string_representation(self, publisher_group_with_news_map):
        representation = str(publisher_group_with_news_map)
        assertion = "<PubGroup: 1>\n\ttest_pub"
        assert representation == assertion
