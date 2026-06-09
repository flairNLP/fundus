from fundus import Requires
from fundus.scraping.filter import (
    FilterResultWithMissingAttributes,
    RequiresAll,
    inverse,
    land,
    lor,
    regex_filter,
)


class TestFilterResultWithMissingAttributes:
    def test_false_when_no_missing_attributes(self):
        assert not FilterResultWithMissingAttributes()

    def test_true_when_has_missing_attributes(self):
        assert FilterResultWithMissingAttributes("title")

    def test_stores_all_missing_attributes(self):
        result = FilterResultWithMissingAttributes("title", "body")
        assert sorted(result.missing_attributes) == ["body", "title"]


class TestRequires:
    def test_passes_when_attribute_is_truthy(self):
        assert not Requires("a")({"a": "text"})

    def test_filtered_when_attribute_is_falsy(self):
        assert Requires("a")({"a": []})

    def test_filtered_when_attribute_is_missing(self):
        assert Requires("a")({"b": "text"})

    def test_filtered_when_boolean_false(self):
        assert Requires("a")({"a": False})

    def test_passes_when_boolean_false_and_eval_disabled(self):
        assert not Requires("a", eval_booleans=False)({"a": False})

    def test_reports_all_failing_attributes(self):
        result = Requires("a", "b")({"a": [], "b": []})
        assert sorted(result.missing_attributes) == ["a", "b"]

    def test_without_arguments_evaluates_all_keys(self):
        result = Requires()({"a": "text", "b": []})
        assert result.missing_attributes == ("b",)


class TestRequiresAll:
    def test_reports_all_falsy_attributes_across_all_keys(self):
        result = RequiresAll()({"a": [], "b": []})
        assert sorted(result.missing_attributes) == ["a", "b"]

    def test_skips_boolean_attributes_by_default(self):
        assert not RequiresAll()({"a": "text", "b": False})

    def test_evaluates_boolean_attributes_when_enabled(self):
        assert RequiresAll(eval_booleans=True)({"a": "text", "b": False})


class TestInverse:
    def test_true_becomes_false(self):
        assert not inverse(lambda url: True)("https://example.com")

    def test_false_becomes_true(self):
        assert inverse(lambda url: False)("https://example.com")

    def test_double_inverse_preserves_result(self):
        def starts_with_https(url: str) -> bool:
            return url.startswith("https")

        assert inverse(inverse(starts_with_https))("https://example.com") is True
        assert inverse(inverse(starts_with_https))("http://example.com") is False


class TestLor:
    def test_true_if_any_filter_matches(self):
        assert lor(lambda url: False, lambda url: True)("https://example.com")

    def test_false_if_no_filter_matches(self):
        assert not lor(lambda url: False, lambda url: False)("https://example.com")

    def test_true_if_all_filters_match(self):
        assert lor(lambda url: True, lambda url: True)("https://example.com")


class TestLand:
    def test_true_if_all_filters_match(self):
        assert land(lambda url: True, lambda url: True)("https://example.com")

    def test_false_if_any_filter_misses(self):
        assert not land(lambda url: True, lambda url: False)("https://example.com")

    def test_false_if_no_filter_matches(self):
        assert not land(lambda url: False, lambda url: False)("https://example.com")


class TestCombinatorNesting:
    def test_inverse_of_lor(self):
        # NOT (A OR B) — true only when both false
        f = inverse(lor(lambda url: False, lambda url: False))
        assert f("https://example.com")
        f = inverse(lor(lambda url: True, lambda url: False))
        assert not f("https://example.com")

    def test_inverse_of_land(self):
        # NOT (A AND B) — true when at least one is false
        f = inverse(land(lambda url: True, lambda url: False))
        assert f("https://example.com")
        f = inverse(land(lambda url: True, lambda url: True))
        assert not f("https://example.com")

    def test_land_of_lors(self):
        # (A OR B) AND (C OR D)
        a_or_b = lor(lambda url: True, lambda url: False)
        c_or_d = lor(lambda url: False, lambda url: False)
        assert not land(a_or_b, c_or_d)("https://example.com")

        a_or_b = lor(lambda url: True, lambda url: False)
        c_or_d = lor(lambda url: False, lambda url: True)
        assert land(a_or_b, c_or_d)("https://example.com")

    def test_lor_of_lands(self):
        # (A AND B) OR (C AND D)
        a_and_b = land(lambda url: True, lambda url: False)
        c_and_d = land(lambda url: True, lambda url: True)
        assert lor(a_and_b, c_and_d)("https://example.com")

        a_and_b = land(lambda url: False, lambda url: False)
        c_and_d = land(lambda url: True, lambda url: False)
        assert not lor(a_and_b, c_and_d)("https://example.com")


class TestRegexFilter:
    def test_matches_pattern(self):
        assert regex_filter(r"/article/\d+")("https://example.com/article/123")

    def test_no_match_returns_false(self):
        assert not regex_filter(r"/article/\d+")("https://example.com/news/latest")

    def test_partial_match_is_sufficient(self):
        assert regex_filter(r"example")("https://example.com/some/deep/path")

    def test_anchored_pattern_matches(self):
        assert regex_filter(r"^https://")("https://example.com")

    def test_anchored_pattern_rejects(self):
        assert not regex_filter(r"^https://")("http://example.com")

    def test_composable_with_inverse(self):
        not_article = inverse(regex_filter(r"/article/"))
        assert not_article("https://example.com/news/1")
        assert not not_article("https://example.com/article/1")
