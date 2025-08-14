from fundus import Requires
from fundus.scraping.filter import RequiresAll


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

        assert not Requires("c", eval_booleans=False)(extraction)

    def test_requires_all(self):
        extraction = {"a": "Some Stuff", "b": [], "c": False}

        assert (result := RequiresAll()(extraction))
        assert result.missing_attributes == ("b",)

        extraction = {"a": "Some Stuff", "c": False}
        assert not RequiresAll()(extraction)

        # test skip_boolean=False
        extraction = {"a": "Some Stuff", "b": [], "c": False}

        assert (result := RequiresAll(eval_booleans=True)(extraction))
        assert sorted(result.missing_attributes) == sorted(("b", "c"))

        extraction = {"a": "Some Stuff", "c": True}
        assert not RequiresAll(eval_booleans=True)(extraction)
