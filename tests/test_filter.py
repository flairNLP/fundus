from fundus import Requires
from fundus.scraping.filter import RequiresAll, RequiresAllSkipBoolean


class TestExtractionFilter:
    def test_requires(self):
        extraction = {"a": "Some Stuff", "b": [], "c": True}

        assert not Requires("a")(extraction)

        assert (result := Requires("a", "b")(extraction))

        assert result.missing_attributes == ("b",)

        assert not Requires("c")(extraction)

        extraction = {"a": "Some Stuff", "b": [], "c": False}

        assert (result := Requires("a", "b", "c")(extraction))

        assert sorted(result.missing_attributes) == sorted(("b", "c"))

        assert not Requires("c", skip_bool=True)(extraction)

    def test_requires_all(self):
        extraction = {"a": "Some Stuff", "b": [], "c": False}

        assert (result := RequiresAll()(extraction))
        assert sorted(result.missing_attributes) == sorted(("b", "c"))

        extraction = {"a": "Some Stuff", "c": True}
        assert not RequiresAll()(extraction)

    def test_requires_all_skip_bool(self):
        extraction = {"a": "Some Stuff", "b": [], "c": False}

        assert (result := RequiresAllSkipBoolean()(extraction))
        assert result.missing_attributes == ("b",)

        extraction = {"a": "Some Stuff", "c": False}
        assert not RequiresAllSkipBoolean()(extraction)
