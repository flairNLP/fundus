from typing import Any, Dict, List

from lxml.etree import XPath

from fundus.parser.data import LinkedDataMapping

lds: List[Dict[str, Any]] = [
    {"@type": "Example1", "value": 1, "data": {"inner": "value", "nested": {"dict": True}}},
    {"@type": "Example2", "value": 2, "_:*@": "Howdy"},
    {"this": "should", "be": {"of": "type", "__UNKNOWN_TYPE__": True, "value": 3}},
]


class TestLinkedDataMapping:
    def test_constructor(self):
        LinkedDataMapping(lds)

    def test_xpath_search(self):
        ld = LinkedDataMapping(lds)
        assert ld.xpath_search(XPath("//value")) == ["1", "2", "3"]
        assert ld.xpath_search(XPath("//UNKNOWN_TYPE//value")) == ["3"]
        assert ld.xpath_search(XPath("//_U003AU002AU0040")) == ["Howdy"]
        assert ld.xpath_search(XPath("//dict")) == ["True"]
        assert ld.xpath_search(XPath("//Example2")) == [{"@type": "Example2", "value": "2", "_:*@": "Howdy"}]
