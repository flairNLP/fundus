from __future__ import annotations

import re
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    TypeVar,
    Union,
    overload,
)

import lxml.etree
import lxml.html
import more_itertools
import xmltodict
from dict2xml import dict2xml
from lxml.etree import XPath, fromstring, tostring
from typing_extensions import TypeAlias, deprecated

from fundus.utils.serialization import JSONVal, replace_keys_in_nested_dict

LDMappingValue: TypeAlias = Union[List[Dict[str, Any]], Dict[str, Any]]

_sentinel = object()

_T = TypeVar("_T")


class LinkedDataMapping:
    """
    This class is a @type -> LD mapping.
    Given LD:
        ld_1 = {
            @type: 'Article'
            ...
            ...
        }
    Article will be mapped to ld_1

    If there are multiple LDs with the same type, this type will map to a list of LDs.
    In this context an LD is represented as a python dict.
    """

    __UNKNOWN_TYPE__ = "UNKNOWN_TYPE"
    __to_transform__ = [":", "*", "@"]
    __xml_transformation_table__ = {char: f"U{ord(char):04X}" for char in __to_transform__}

    def __init__(self, lds: Iterable[Dict[str, Any]] = ()):
        for ld in lds:
            if graph := ld.get("@graph"):
                for nested in graph:
                    self.add_ld(nested)
            else:
                self.add_ld(ld)
        self.__xml: Optional[lxml.etree.Element] = None

    def __getstate__(self):
        state = self.__dict__.copy()
        if self.__xml is not None:
            state["_LinkedDataMapping__xml"] = tostring(self.__xml)
        return state

    def __setstate__(self, state):
        if (xml_element := state.get("_LinkedDataMapping__xml")) is not None:
            state["_LinkedDataMapping__xml"] = fromstring(xml_element)
        self.__dict__ = state

    def serialize(self) -> Dict[str, Any]:
        return {attribute: value for attribute, value in self.__dict__.items() if "__" not in attribute}

    def _add(self, ld: Dict[str, JSONVal], ld_type: str) -> None:
        if value := self.__dict__.get(ld_type):
            if not isinstance(value, list):
                self.__dict__[ld_type] = [value]
            self.__dict__[ld_type].append(ld)
        else:
            self.__dict__[ld_type] = ld

    def add_ld(self, ld: Dict[str, Any], name: Optional[str] = None) -> None:
        if ld_type := (name or ld.get("@type")):
            if isinstance(ld_type, str):
                self._add(ld, ld_type)
            elif isinstance(ld_type, list):
                for t in ld_type:
                    self._add(ld, t)
            else:
                raise NotImplementedError(f"Unexpected LD type {type(ld_type)}")
        else:
            self._add(ld, self.__UNKNOWN_TYPE__)

    @deprecated("Use xpath_search() instead")
    def get_value_by_key_path(self, key_path: List[str], default: Any = None) -> Optional[Any]:
        """
        Works like get() except this one assumes a path is given as list of keys (str).
        I.e:
            key_path := ["mainEntity", "author"], default := {}
            results in self._ld_by_type.get("mainEntity").get("author")

        Whenever a key is missing or an empty value occurs down the path this funktion will immediately return
        <default>, but will not catch if not all values supports get()

        :param key_path: A list of keys in order forming a path to the desired value
        :param default: A default returned when either a key is missing or resulting in an empty/null value
        :return: The reached value or <default>
        """
        tmp = self.__dict__.copy()
        for key in key_path:
            if not (nxt := tmp.get(key)):
                return default
            tmp = nxt
        return tmp

    def __as_xml__(self) -> lxml.etree.Element:
        pattern = re.compile("|".join(map(re.escape, self.__xml_transformation_table__.keys())))

        def to_unicode_characters(text: str) -> str:
            return pattern.sub(lambda match: self.__xml_transformation_table__[match.group(0)], text)

        if self.__xml is None:
            xml = dict2xml(replace_keys_in_nested_dict({"linkedData": self.serialize()}, to_unicode_characters))
            self.__xml = lxml.etree.fromstring(xml)
        return self.__xml

    __value_regex__ = re.compile("^<[^<]*>(?P<value>.*)</[^<]*>$", flags=re.DOTALL)
    __empty_tag_regex__ = re.compile("^<[^<]*/>$", flags=re.DOTALL)

    @overload
    def xpath_search(self, query: Union[XPath, str], scalar: Literal[False] = False) -> List[Any]: ...

    @overload
    def xpath_search(self, query: Union[XPath, str], scalar: Literal[True] = True) -> Optional[Any]: ...

    def xpath_search(self, query: Union[XPath, str], scalar: bool = False):
        """Search through LD using XPath expressions

        Internally, the content of the LinkedDataMapping is converted to XML and then
        evaluated with an XPath expression <query>.

        To search for keys including invalid XML characters, use Unicode representations instead:
        I.e. to search for the key "_16:9" write "//_16U003A9"
        For all available transformations see LinkedDataMapping.__xml_transformation_table__

        Note that values will be converted to strings, i.e. True -> 'True', 1 -> '1'

        Examples:
            LinkedDataMapping = {
                "b": {
                    "key": value1,
                }
                "c": {
                    "key": value2,
                }
            }

        LinkedDataMapping.xpath_search(XPath("//key"))
        >> [value1, value2]

        LinkedDataMapping.xpath_search(XPath("//b/key"))
        >> [value1]

        Args:
            query: A XPath expression either as string or XPath object.
            scalar: If True, return an optional "scalar" value and raise a ValueError if there are more
                than one result to return; if False, return a list of results. Defaults to False.

        Returns:
            An ordered list of search results or an optional "scalar" result
        """

        if isinstance(query, str):
            query = XPath(query)

        pattern = re.compile("|".join(map(re.escape, self.__xml_transformation_table__.values())))

        def node2string(n: lxml.etree.Element) -> str:
            node_value = lxml.etree.tostring(n, encoding="unicode").strip()
            if match := self.__value_regex__.match(node_value):
                return match.group("value")
            if self.__empty_tag_regex__.match(node_value):
                return ""
            raise ValueError("XML malformed. Could not determine value.")

        reversed_table = {v: k for k, v in self.__xml_transformation_table__.items()}

        def to_original_characters(text: str) -> str:
            return pattern.sub(lambda match: reversed_table[match.group(0)], text)

        nodes = query(self.__as_xml__())

        results = {}

        for i, node in enumerate(nodes):
            xml = f"<result{i}>" + node2string(node) + f"</result{i}>"
            results.update(replace_keys_in_nested_dict(xmltodict.parse(xml), to_original_characters))

        values = list(filter(bool, results.values()))

        if scalar:
            if not values:
                return None
            elif len(values) == 1:
                return values.pop()
            else:
                raise ValueError("Got multiple values when expecting a single scalar value")
        else:
            return values

    def bf_search(self, key: str, depth: Optional[int] = None, default: Optional[_T] = None) -> Union[Any, _T]:
        """
        This is a classic BF search on the nested dicts representing the JSON-LD. <key> specifies the dict key to
        search, <depth> the depth level. If the depth level is set to None, this method will search through the whole
        LD. It is important to notice that this will only return the value of the first matched key.
        For more precise operations consider using get_by_key_path().

        I.e:

            considering the following LD:
                MainPage
                    @type
                    @content
                    BreadcrumbList
                        ...
                        ...
                    NewsArticle
                        datePublished: ...
                        authors: ...

            the contents of 'MainPage' count as depth 1.

            So
                breadth_first_search('authors') -> None,

            whereas

                breadth_first_search('@content') -> the value of key '@content'

            and

                breadth_first_search('authors', 2) -> the value of key 'authors'

        :param key: The dict key to search for
        :param depth: The searched depth, default None
        :return: The content of the first matched key or None
        """

        def search_recursive(nodes: Iterable[LDMappingValue], current_depth: int):
            if current_depth == depth:
                return _sentinel
            else:
                new: List[Dict[str, Any]] = []
                for node in nodes:
                    if isinstance(node, list):
                        new.extend(node)
                        continue
                    elif (value := node.get(key, _sentinel)) is not _sentinel:
                        return value

                    nested_dicts: Iterable[Dict[str, Any]] = filter(
                        lambda obj: isinstance(obj, dict), more_itertools.collapse(node.values(), base_type=dict)
                    )
                    new.extend(nested_dicts)

                if not new:
                    return _sentinel

                return search_recursive(new, current_depth + 1)

        result = search_recursive([self.__dict__], 0)

        if result == _sentinel:
            return default

        return result

    def __repr__(self):
        return f"LD containing {', '.join(content)!r}" if (content := self.__dict__.keys()) else "Empty LD"
