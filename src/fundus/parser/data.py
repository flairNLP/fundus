from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
from functools import total_ordering
from typing import (
    Any,
    ClassVar,
    Collection,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    overload,
)
from urllib.parse import urljoin, urlparse

import lxml.html
import more_itertools
import validators
from typing_extensions import Self, TypeAlias

from fundus.utils.serialization import DataclassSerializationMixin

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

    def __init__(self, lds: Iterable[Dict[str, Any]] = ()):
        for ld in lds:
            if graph := ld.get("@graph"):
                for nested in graph:
                    self.add_ld(nested)
            else:
                self.add_ld(ld)

    def serialize(self) -> Dict[str, Any]:
        return {attribute: value for attribute, value in self.__dict__.items() if "__" not in attribute}

    def add_ld(self, ld: Dict[str, Any], name: Optional[str] = None) -> None:
        if ld_type := ld.get("@type", name):
            if isinstance(ld_type, list):
                if len(ld_type) == 1:
                    ld_type = ld_type[0]
                else:
                    raise TypeError(f"Unable tp parse ld_type '{ld_type}' of type {list} with length != 1")
            if value := self.__dict__.get(ld_type):
                if not isinstance(value, list):
                    self.__dict__[ld_type] = [value]
                self.__dict__[ld_type].append(ld)
            else:
                self.__dict__[ld_type] = ld
        else:
            if not self.__dict__.get(self.__UNKNOWN_TYPE__):
                self.__dict__[self.__UNKNOWN_TYPE__] = []
            self.__dict__[self.__UNKNOWN_TYPE__].append(ld)

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


@total_ordering
@dataclass
class Dimension(DataclassSerializationMixin):
    width: int
    height: int

    def __mul__(self, other: Union[float, int]) -> "Dimension":
        if isinstance(other, int):
            return Dimension(self.width * other, self.height * other)
        elif isinstance(other, float):
            return Dimension(round(self.width * other), round(self.height * other))
        else:
            raise NotImplementedError(
                f"'*' is not defined between {type(self).__name__!r} and {type(other).__name__!r}"
            )

    def __rmul__(self, other: Union[float, int]) -> "Dimension":
        return self.__mul__(other)

    def __repr__(self) -> str:
        return f"{self.width}x{self.height or '...'}"

    def __lt__(self, other: "Dimension") -> bool:
        if isinstance(other, Dimension):
            if self.width != other.width:
                return self.width < other.width
            else:
                return self.height < other.height
        raise NotImplementedError(f"'<' is not defined between {type(self).__name__!r} and {type(other).__name__!r}")

    def __hash__(self) -> int:
        return hash((self.width, self.height))

    @classmethod
    def from_ratio(
        cls,
        width: Optional[float] = None,
        height: Optional[float] = None,
        ratio: Optional[float] = None,
    ) -> Optional["Dimension"]:
        if width and height:
            return cls(round(width), round(height))
        elif width is not None:
            return cls(round(width), round((width / ratio) if ratio else 0))
        elif height is not None:
            return cls(round((height * ratio) if ratio else 0), round(height))
        else:
            return None


def remove_query_parameters_from_url(url: str) -> str:
    if any(parameter_indicator in url for parameter_indicator in ("?", "#")):
        return urljoin(url, urlparse(url).path)
    return url


@total_ordering
@dataclass
class ImageVersion(DataclassSerializationMixin):
    __FILE_FORMATS__: ClassVar[List[str]] = ["png", "jpg", "jpeg", "webp"]

    url: str
    query_width: Optional[str] = None
    size: Optional[Dimension] = None
    type: Optional[str] = None

    def __post_init__(self):
        if not self.type:
            url_without_query = remove_query_parameters_from_url(self.url)
            self.type = self._parse_type(url_without_query)

    def _parse_type(self, url: str) -> Optional[str]:
        if (file_format := url.split(".")[-1]) in self.__FILE_FORMATS__:
            if file_format == "jpg":
                file_format = "jpeg"
            return "image/" + file_format
        return None

    def __repr__(self) -> str:
        if self.size is not None:
            meta = f"{self.size!r}"
        elif self.query_width is not None:
            meta = f"min-width: {self.query_width}px"
        else:
            meta = f"{type(self).__name__}"

        return f"{meta}; {self.type}"

    def __hash__(self) -> int:
        return hash(self.url)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ImageVersion):
            return NotImplemented
        return self.url == other.url

    def __lt__(self, other: "Dimension") -> bool:
        if isinstance(other, ImageVersion):
            if self.size and other.size:
                if self.size == other.size:
                    return self.type < other.type if self.type and other.type else self.url < other.url
                return self.size < other.size
            elif self.query_width and other.query_width:
                if self.query_width == other.query_width:
                    return self.type < other.type if self.type and other.type else self.url < other.url
                return self.query_width < other.query_width
            else:
                return True
        raise NotImplementedError(f"'<' is not defined between {type(self).__name__!r} and {type(other).__name__!r}")


@dataclass(frozen=False)
class Image(DataclassSerializationMixin):
    versions: List[ImageVersion]
    is_cover: bool
    description: Optional[str]
    caption: Optional[str]
    authors: List[str]
    position: int

    def __post_init__(self):
        for url in [version.url for version in self.versions]:
            if not validators.url(url, strict_query=False):
                raise ValueError(f"url {url} is not a valid URL")

    @property
    def url(self) -> str:
        return self.versions[-1].url

    def __str__(self) -> str:
        if self.is_cover:
            representation = "Fundus-Article Cover-Image:\n"
        else:
            representation = "Fundus-Article Image:\n"
        representation += (
            f"-URL:\t\t\t {self.url!r}\n"
            f"-Description:\t {self.description!r}\n"
            f"-Caption:\t\t {self.caption!r}\n"
            f"-Authors:\t\t {self.authors}\n"
            f"-Sizes:\t\t\t {sorted(set(v.size for v in self.versions if v.size is not None))}\n"
        )
        return representation

    def __repr__(self) -> str:
        return self.url


class DOM:
    def __init__(self, root: lxml.html.HtmlElement):
        self.root = root
        self._depth_first_index = {element: i for i, element in enumerate(root.iter())}

    def get_index(self, node: lxml.html.HtmlElement) -> int:
        return self._depth_first_index[node]
