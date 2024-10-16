import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
from itertools import chain
from typing import (
    Any,
    Collection,
    Dict,
    Iterable,
    Iterator,
    List,
    Literal,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    overload,
)

import lxml.etree
import more_itertools
import xmltodict
from dict2xml import dict2xml
from lxml.etree import XPath, tostring
from typing_extensions import Self, TypeAlias, deprecated

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
    __xml_transformation_table__ = {":": "U003A", "*": "U002A", "@": "U0040"}

    def __init__(self, lds: Iterable[Dict[str, Any]] = ()):
        for ld in lds:
            if graph := ld.get("@graph"):
                for nested in graph:
                    self.add_ld(nested)
            else:
                self.add_ld(ld)
        self.__xml: Optional[lxml.etree._Element] = None

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

    def __as_xml__(self) -> lxml.etree._Element:
        pattern = re.compile("|".join(map(re.escape, self.__xml_transformation_table__.keys())))

        def to_unicode_characters(text: str) -> str:
            return pattern.sub(lambda match: self.__xml_transformation_table__[match.group(0)], text)

        if self.__xml is None:
            xml = dict2xml(replace_keys_in_nested_dict({"linkedData": self.serialize()}, to_unicode_characters))
            self.__xml = lxml.etree.fromstring(xml)
        return self.__xml

    @overload
    def xpath_search(self, query: Union[XPath, str], scalar: Literal[False] = False) -> List[Any]:
        ...

    @overload
    def xpath_search(self, query: Union[XPath, str], scalar: Literal[True] = True) -> Optional[Any]:
        ...

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

        def node2string(n: lxml.etree._Element) -> str:
            return "".join(
                chunk
                for chunk in chain(
                    (n.text,),
                    chain(*((tostring(child, with_tail=False, encoding=str), child.tail) for child in n.getchildren())),
                )
                if chunk
            )

        reversed_table = {v: k for k, v in self.__xml_transformation_table__.items()}

        def to_original_characters(text: str) -> str:
            return pattern.sub(lambda match: reversed_table[match.group(0)], text)

        nodes = query(self.__as_xml__())

        results = {}

        for i, node in enumerate(nodes):
            xml = f"<result{i}>" + node2string(node) + f"</result{i}>"
            results.update(replace_keys_in_nested_dict(xmltodict.parse(xml), to_original_characters))

        values = list(results.values())

        if scalar:
            if not values:
                return None
            elif len(values) == 1:
                return values.pop()
            else:
                raise ValueError(f"Got multiple values when expecting a single scalar value")
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


class TextSequence(Sequence[str]):
    def __init__(self, texts: Iterable[str]):
        self._data: Tuple[str, ...] = tuple(texts)

    @overload
    def __getitem__(self, i: int) -> str:
        ...

    @overload
    def __getitem__(self, s: slice) -> "TextSequence":
        ...

    def __getitem__(self, i):
        return self._data[i] if isinstance(i, int) else type(self)(self._data[i])

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self) -> Iterator[str]:
        return iter(self._data)

    def __repr__(self) -> str:
        return repr(self._data)

    def __str__(self) -> str:
        return "\n".join(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TextSequence):
            return NotImplemented
        return self._data == other._data


@dataclass
class TextSequenceTree(ABC):
    """Base class to traverse and build trees of TextSequence."""

    def as_text_sequence(self) -> TextSequence:
        texts = [text for tl in self.df_traversal() for text in tl]
        return TextSequence(texts)

    def text(self, join_on: str = "\n\n") -> str:
        return join_on.join(self.as_text_sequence())

    def df_traversal(self) -> Iterable[TextSequence]:
        def recursion(o: object):
            if isinstance(o, TextSequence):
                yield o
            elif isinstance(o, Collection):
                for el in o:
                    yield from el
            else:
                yield o

        for value in self:
            yield from recursion(value)

    @abstractmethod
    def serialize(self) -> Dict[str, Any]:
        pass

    @classmethod
    @abstractmethod
    def deserialize(cls, serialized: Dict[str, Any]) -> Self:
        pass

    def __iter__(self) -> Iterator[Any]:
        field_values = [getattr(self, f.name) for f in fields(self)]
        yield from field_values

    def __str__(self):
        return self.text()

    def __bool__(self) -> bool:
        return bool(self.as_text_sequence())


@dataclass
class ArticleSection(TextSequenceTree):
    headline: TextSequence
    paragraphs: TextSequence

    def serialize(self) -> Dict[str, Any]:
        return {
            "headline": list(self.headline),
            "paragraphs": list(self.paragraphs),
        }

    @classmethod
    def deserialize(cls, serialized: Dict[str, Any]) -> Self:
        return cls(headline=TextSequence(serialized["headline"]), paragraphs=TextSequence(serialized["paragraphs"]))

    def __bool__(self):
        return bool(self.paragraphs)


@dataclass
class ArticleBody(TextSequenceTree):
    summary: TextSequence
    sections: List[ArticleSection]

    def serialize(self) -> Dict[str, Any]:
        return {
            "summary": list(self.summary),
            "sections": [section.serialize() for section in self.sections],
        }

    @classmethod
    def deserialize(cls, serialized: Dict[str, Any]) -> Self:
        return cls(
            summary=TextSequence(serialized["summary"]),
            sections=[ArticleSection.deserialize(section) for section in serialized["sections"]],
        )

    def __bool__(self):
        return any(bool(section) for section in self.sections)
