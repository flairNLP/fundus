from pickle import dumps, loads
from typing import Any, Dict, List

from lxml.etree import XPath, tostring

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

    def test_pickle(self):
        ld = LinkedDataMapping(lds)
        ld.__as_xml__()
        ld_pickled = loads(dumps(ld))
        assert ld_pickled.__getattribute__("Example1") == ld.__getattribute__("Example1")
        assert ld_pickled.__getattribute__("Example2") == ld.__getattribute__("Example2")
        assert ld_pickled.__getattribute__("UNKNOWN_TYPE") == ld.__getattribute__("UNKNOWN_TYPE")
        assert tostring(ld_pickled.__getattribute__("_LinkedDataMapping__xml")) == tostring(
            ld.__getattribute__("_LinkedDataMapping__xml")
        )
