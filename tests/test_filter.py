from typing import Any, Dict

from fundus import Requires
from fundus.scraping.filter import RequiresAll


class TestExtractionFilter:
    def test_requires(self):
        extraction: Dict[str, Dict[str, Any]] = {
            "a": {"value": "Some Stuff", "deprecated": False},
            "b": {"value": [], "deprecated": False},
            "c": {"value": True, "deprecated": False},
        }

        assert not Requires("a")(extraction)

        assert (result := Requires("a", "b")(extraction))

        assert result.missing_attributes == ("b",)

        assert not Requires("c")(extraction)

        extraction = {
            "a": {"value": "Some Stuff", "deprecated": False},
            "b": {"value": [], "deprecated": False},
            "c": {"value": False, "deprecated": False},
        }

        assert (result := Requires("a", "b", "c")(extraction))

        assert sorted(result.missing_attributes) == sorted(("b", "c"))

        assert not Requires("c", eval_booleans=False)(extraction)

    def test_requires_all(self):
        extraction: Dict[str, Dict[str, Any]] = {
            "a": {"value": "Some Stuff", "deprecated": False},
            "b": {"value": [], "deprecated": False},
            "c": {"value": False, "deprecated": False},
        }

        assert (result := RequiresAll()(extraction))
        assert result.missing_attributes == ("b",)

        extraction = {
            "a": {"value": "Some Stuff", "deprecated": False},
            "c": {"value": False, "deprecated": False},
        }
        assert not RequiresAll()(extraction)

        # test skip_boolean=False
        extraction = {
            "a": {"value": "Some Stuff", "deprecated": False},
            "b": {"value": [], "deprecated": False},
            "c": {"value": False, "deprecated": False},
        }

        assert (result := RequiresAll(eval_booleans=True)(extraction))
        assert sorted(result.missing_attributes) == sorted(("b", "c"))

        extraction = {
            "a": {"value": "Some Stuff", "deprecated": False},
            "c": {"value": True, "deprecated": False},
        }
        assert not RequiresAll(eval_booleans=True)(extraction)

    def test_deprecation(self):
        extraction: Dict[str, Dict[str, Any]] = {
            "a": {"value": None, "deprecated": True},
            "b": {"value": ["List", "is", "not", "empty"], "deprecated": False},
            "c": {"value": False, "deprecated": False},
        }
        assert RequiresAll(force_deprecated=True)(extraction)
        assert not RequiresAll(force_deprecated=False)(extraction)
