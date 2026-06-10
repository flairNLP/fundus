from unittest.mock import MagicMock, patch

import pytest
from curl_cffi.requests.exceptions import ConnectionError, ReadTimeout

from fundus import NewsMap, RSSFeed, Sitemap
from fundus.publishers.base_objects import CustomRobotFileParser, FilteredPublisher, Robots
from fundus.scraping.session import session_handler
from tests.fixtures.builders import make_http_error, make_publisher, make_publisher_group, mock_response


class TestPublisherSupports:
    """`supports` answers: is there a *single* source matching the given (type AND language)?"""

    def test_unconstrained_matches_publisher_with_sources(self):
        publisher = make_publisher(sources=[NewsMap("https://x/news", languages={"en"})])
        assert publisher.supports() is True

    @pytest.mark.parametrize("source_type, expected", [(NewsMap, True), (Sitemap, False)])
    def test_filters_by_source_type(self, source_type, expected):
        publisher = make_publisher(sources=[NewsMap("https://x/news", languages={"en"})])
        assert publisher.supports(source_types=[source_type]) is expected

    @pytest.mark.parametrize("language, expected", [("es", True), ("de", True), ("fr", False)])
    def test_filters_by_language(self, language, expected):
        publisher = make_publisher(
            sources=[
                RSSFeed("https://x/feed", languages={"es"}),
                Sitemap("https://x/map", languages={"de"}),
            ]
        )
        assert publisher.supports(languages=[language]) is expected

    @pytest.mark.parametrize(
        "source_type, language, expected",
        [
            (NewsMap, "es", True),  # the NewsMap source carries 'es'
            (RSSFeed, "pl", True),  # the RSSFeed source carries 'pl'
            (NewsMap, "pl", False),  # 'pl' exists, but only on the RSSFeed — no single source is both
            (RSSFeed, "es", False),  # 'es' exists, but only on the NewsMap
        ],
    )
    def test_requires_one_source_matching_both_type_and_language(self, source_type, language, expected):
        publisher = make_publisher(
            sources=[
                RSSFeed("https://x/feed", languages={"pl"}),
                NewsMap("https://x/news", languages={"es"}),
            ]
        )
        assert publisher.supports(source_types=[source_type], languages=[language]) is expected


class TestPublisherGroup:
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

    def test_string_representation_nests_subgroups_and_publishers(self):
        group = make_publisher_group(
            name="Root",
            news=make_publisher_group(name="News", a=make_publisher(name="pub_a")),
            sitemap=make_publisher_group(name="Sitemap", b=make_publisher(name="pub_b")),
        )
        assert str(group) == "<Root: 2>\n\t<News: 1>\n\t\tpub_a\n\t<Sitemap: 1>\n\t\tpub_b"

    def test_string_representation_lists_direct_publishers(self):
        group = make_publisher_group(name="PubGroup", value=make_publisher(name="test_pub"))
        assert str(group) == "<PubGroup: 1>\n\ttest_pub"


@pytest.mark.filterwarnings("ignore::UserWarning")  # searches that match nothing call warn()
class TestPublisherGroupSearch:
    @pytest.mark.parametrize("args", [(), ([],), ([], [])])
    def test_requires_at_least_one_criterion(self, args):
        with pytest.raises(ValueError):
            make_publisher_group().search(*args)

    def test_matches_only_attributes_of_the_active_parser_version(
        self, publisher_group_with_versioned_attrs, proxy_with_two_versions_and_different_attrs
    ):
        # the publisher's active parser is the latest version, so only its attributes are searchable
        current, superseded = proxy_with_two_versions_and_different_attrs().attribute_mapping.values()
        assert len(publisher_group_with_versioned_attrs.search(current.names)) == 1
        assert publisher_group_with_versioned_attrs.search(superseded.names) == []

    @pytest.mark.parametrize("source_types, expected", [([NewsMap], 1), ([Sitemap], 0)])
    def test_combines_attribute_match_with_source_constraint(
        self, publisher_group_with_versioned_attrs, proxy_with_two_versions_and_different_attrs, source_types, expected
    ):
        # attributes match, but the publisher only has a NewsMap source
        current, _ = proxy_with_two_versions_and_different_attrs().attribute_mapping.values()
        assert len(publisher_group_with_versioned_attrs.search(current.names, source_types=source_types)) == expected

    def test_excludes_deprecated_attributes_by_default(
        self, publisher_group_with_deprecated_attrs, proxy_with_two_deprecated_attributes
    ):
        (attributes,) = proxy_with_two_deprecated_attributes().attribute_mapping.values()
        assert publisher_group_with_deprecated_attrs.search([attributes.deprecated.names[0]]) == []

    def test_includes_deprecated_attributes_when_requested(
        self, publisher_group_with_deprecated_attrs, proxy_with_two_deprecated_attributes
    ):
        (attributes,) = proxy_with_two_deprecated_attributes().attribute_mapping.values()
        result = publisher_group_with_deprecated_attrs.search(
            [attributes.deprecated.names[0]], include_deprecated_attributes=True
        )
        assert len(result) == 1

    def test_returns_every_matching_publisher(self):
        group = make_publisher_group(
            default_language="en",  # eng's source declares no language, so it inherits "en"
            eng=make_publisher(name="eng", sources=[NewsMap("https://x/news")]),
            ger=make_publisher(name="ger", sources=[Sitemap("https://x/map", languages={"de"})]),
        )
        # search collects every publisher in the group that matches
        assert len(group.search(languages=["en"])) == 1
        assert len(group.search(languages=["de"])) == 1
        assert len(group.search(languages=["en", "de"])) == 2

    def test_returns_results_narrowed_to_search_criteria(self):
        group = make_publisher_group(value=make_publisher(sources=[NewsMap("https://x/n"), Sitemap("https://x/s")]))
        (result,) = group.search(source_types=[NewsMap])
        assert set(result.source_mapping) == {NewsMap}  # Sitemap dropped; result is a narrowed FilteredPublisher


@pytest.fixture
def robots_session():
    """Patch the session_handler that CustomRobotFileParser.read() reaches for; yield the session mock."""
    with patch("fundus.publishers.base_objects.session_handler") as handler:
        session = MagicMock()
        handler.get_session.return_value = session
        yield session


class TestCustomRobotFileParser:
    @pytest.mark.parametrize(
        "lines, expected",
        [
            (["# we allow machine learning training"], True),  # keyword inside a comment
            (["# just an ordinary comment"], False),  # comment, no keyword
            (["User-agent: *", "Disallow: /machine"], False),  # keyword token, but not a comment line
        ],
    )
    def test_parse_detects_disallow_training_in_comments(self, lines, expected):
        parser = CustomRobotFileParser("https://x/robots.txt")
        parser.parse(lines)
        assert parser.disallows_training is expected

    @pytest.mark.parametrize("status", [401, 403])
    def test_read_auth_error_disallows_all(self, robots_session, status):
        robots_session.get_with_interrupt.side_effect = make_http_error(status_code=status)
        parser = CustomRobotFileParser("https://x/robots.txt")
        parser.read()
        assert parser.disallow_all is True

    @pytest.mark.parametrize("status", [400, 404, 429, 500, 503])
    def test_read_error_defaults_to_allow_all(self, robots_session, status):
        # any non-401/403 HTTP error (missing robots.txt or a server error) → treat as no restrictions
        robots_session.get_with_interrupt.side_effect = make_http_error(status_code=status)
        parser = CustomRobotFileParser("https://x/robots.txt")
        parser.read()
        assert parser.allow_all is True

    def test_read_success_scans_body_for_disallow_training(self, robots_session):
        robots_session.get_with_interrupt.return_value = mock_response(text="# trained for machine learning")
        parser = CustomRobotFileParser("https://x/robots.txt")
        parser.read()
        assert parser.disallows_training is True

    def test_read_success_enforces_parsed_rules(self, robots_session):
        robots_session.get_with_interrupt.return_value = mock_response(text="User-agent: *\nDisallow: /private")
        parser = CustomRobotFileParser("https://x/robots.txt")
        parser.read()
        assert parser.can_fetch("*", "https://x/private") is False
        assert parser.can_fetch("*", "https://x/public") is True


class TestRobots:
    @pytest.mark.parametrize("raw, expected", [(5, 5.0), (2.5, 2.5), (None, None)])
    def test_crawl_delay_is_coerced_to_float(self, raw, expected):
        robots = Robots("https://x/robots.txt")
        robots.robots_file_parser = MagicMock()
        robots.robots_file_parser.crawl_delay.return_value = raw
        result = robots.crawl_delay("*")
        assert result == expected
        if expected is not None:
            assert isinstance(result, float)

    def test_robots_is_read_once_across_calls(self):
        robots = Robots("https://x/robots.txt")
        robots.robots_file_parser = MagicMock()
        robots.can_fetch("*", "https://x/a")
        robots.crawl_delay("*")
        robots.disallow_all()
        robots.robots_file_parser.read.assert_called_once()

    @pytest.mark.parametrize("error", [ConnectionError("boom"), ReadTimeout("boom")])
    def test_read_failure_is_swallowed_and_allows_all(self, error):
        robots = Robots("https://x/robots.txt")
        robots.robots_file_parser = MagicMock()
        robots.robots_file_parser.read.side_effect = error
        robots.ensure_ready()  # must not raise
        assert robots.robots_file_parser.allow_all is True
        assert robots.ready is True

    @pytest.mark.integration
    @pytest.mark.xfail(
        reason="_read catches ReadTimeout, not the base Timeout curl_cffi raises on a real timeout, so the "
        "timeout propagates out of ensure_ready instead of defaulting to allow-all. Fixed by flairNLP/fundus#939.",
        strict=True,
    )
    def test_real_timeout_is_swallowed_and_allows_all(self, hanging_url):
        robots = Robots(hanging_url)
        with session_handler.context(timeout=0.3):
            robots.ensure_ready()  # must not raise
        assert robots.robots_file_parser.allow_all is True
        assert robots.ready is True

    def test_can_fetch_delegates_to_parser(self):
        robots = Robots("https://x/robots.txt")
        robots.robots_file_parser = MagicMock()
        robots.robots_file_parser.can_fetch.return_value = False
        assert robots.can_fetch("bot", "https://x/p") is False
        robots.robots_file_parser.can_fetch.assert_called_once_with("bot", "https://x/p")


class TestPublisherConstruction:
    @pytest.mark.parametrize("missing", [{"name": ""}, {"domain": ""}, {"sources": []}])
    def test_requires_mandatory_fields(self, missing):
        with pytest.raises(ValueError):
            make_publisher(**missing)

    def test_rejects_non_urlsource_sources(self):
        with pytest.raises(TypeError):
            make_publisher(sources=["https://x/not-a-source"])  # type: ignore[list-item]

    def test_rejects_unknown_impersonate(self):
        with pytest.raises(ValueError):
            make_publisher(impersonate="definitely-not-a-browser")  # type: ignore[arg-type]

    def test_accepts_valid_impersonate(self):
        assert make_publisher(impersonate="chrome").impersonate

    @pytest.mark.parametrize("domain", ["https://x.com/", "https://x.com"])
    def test_robots_url_appends_path(self, domain):
        assert make_publisher(domain=domain).robots.url == "https://x.com/robots.txt"

    def test_orders_sources_rss_newsmap_sitemap(self):
        publisher = make_publisher(
            sources=[
                Sitemap("https://x/sitemap"),
                NewsMap("https://x/news"),
                RSSFeed("https://x/feed"),
            ]
        )
        assert list(publisher.source_mapping) == [RSSFeed, NewsMap, Sitemap]

    def test_suppress_robots_sets_allow_all(self):
        publisher = make_publisher(suppress_robots=True)
        assert publisher.robots.robots_file_parser.allow_all is True


class TestPublisherProperties:
    def test_languages_unions_all_sources(self):
        publisher = make_publisher(
            sources=[
                RSSFeed("https://x/feed", languages={"en", "de"}),
                Sitemap("https://x/map", languages={"fr"}),
            ]
        )
        assert publisher.languages == {"en", "de", "fr"}

    def test_source_types_reflects_present_types(self):
        publisher = make_publisher(sources=[RSSFeed("https://x/feed"), NewsMap("https://x/news")])
        assert publisher.source_types == {RSSFeed, NewsMap}

    def test_disallows_training_short_circuits_on_flag(self):
        publisher = make_publisher(disallows_training=True)
        publisher.robots = MagicMock()
        assert publisher.disallows_training is True
        publisher.robots.disallows_training.assert_not_called()

    def test_disallows_training_falls_back_to_robots(self):
        publisher = make_publisher(disallows_training=False)
        publisher.robots = MagicMock()
        publisher.robots.disallows_training.return_value = True
        assert publisher.disallows_training is True

    def test_disallows_training_false_when_neither(self):
        publisher = make_publisher(disallows_training=False)
        publisher.robots = MagicMock()
        publisher.robots.disallows_training.return_value = False
        assert publisher.disallows_training is False


class TestPublisherEquality:
    def test_hash_is_name_based(self):
        assert hash(make_publisher(name="x")) == hash("x")
        assert hash(make_publisher(name="x")) == hash(make_publisher(name="x"))

    def test_differs_by_name(self):
        assert make_publisher(name="a") != make_publisher(name="b")

    def test_not_equal_to_non_publisher(self):
        assert make_publisher() != "not a publisher"

    def test_equal_to_itself(self):
        publisher = make_publisher()
        assert publisher == publisher

    @pytest.mark.xfail(
        reason="Publisher.__eq__ compares self.parser by identity (ParserProxy defines no __eq__), "
        "so two value-equal publishers never compare equal.",
        strict=True,
    )
    def test_value_equal_publishers_compare_equal(self):
        assert make_publisher(name="x") == make_publisher(name="x")


class TestFilteredPublisher:
    def test_no_filter_exposes_all_sources(self):
        publisher = make_publisher(sources=[NewsMap("https://x/n"), Sitemap("https://x/s")])
        filtered = FilteredPublisher.from_publisher(publisher)
        assert filtered.source_mapping == publisher.source_mapping

    def test_narrows_by_source_type(self):
        publisher = make_publisher(sources=[NewsMap("https://x/n"), Sitemap("https://x/s")])
        filtered = FilteredPublisher.from_publisher(publisher, source_types={NewsMap})
        assert set(filtered.source_mapping) == {NewsMap}

    def test_narrows_by_language(self):
        publisher = make_publisher(
            sources=[RSSFeed("https://x/r", languages={"es"}), Sitemap("https://x/s", languages={"de"})]
        )
        filtered = FilteredPublisher.from_publisher(publisher, languages={"es"})
        assert set(filtered.source_mapping) == {RSSFeed}  # German Sitemap dropped

    def test_combines_source_type_and_language_filters(self):
        publisher = make_publisher(
            sources=[
                RSSFeed("https://x/r", languages={"es"}),
                NewsMap("https://x/n", languages={"es"}),
                Sitemap("https://x/s", languages={"es"}),
            ]
        )
        filtered = FilteredPublisher.from_publisher(publisher, source_types={NewsMap, Sitemap}, languages={"es"})
        assert set(filtered.source_mapping) == {NewsMap, Sitemap}  # RSSFeed excluded by source-type filter

    def test_language_filter_is_exposed(self):
        filtered = FilteredPublisher.from_publisher(make_publisher(), languages={"es"})
        assert filtered.language_filter == {"es"}

    def test_carries_over_publisher_identity(self):
        filtered = FilteredPublisher.from_publisher(make_publisher(name="orig"))
        assert filtered.name == "orig"
