from abc import ABC
from dataclasses import dataclass, fields
from typing import (
    Any,
    Callable,
    ClassVar,
    Collection,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
    overload,
)

from typing_extensions import TypeAlias

from fundus.logging import basic_logger

_displayed_deprecation_info = False

LDMappingValue: TypeAlias = Union[List[Dict[str, Any]], Dict[str, Any]]


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

    def __init__(self, lds: Iterable[Dict[str, Any]] = ()):
        for ld in lds:
            if graph := ld.get("@graph"):
                for nested in graph:
                    self.add_ld(nested)
            else:
                self.add_ld(ld)

    def add_ld(self, ld: Dict[str, Any]) -> None:
        if ld_type := ld.get("@type"):
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
            raise ValueError(f"Found no type for LD")

    def get(self, ld_type: str, default: Any = None) -> Optional[LDMappingValue]:
        """
        This function works like get() on a mapping. It will return all LDs containing
        the given <ld_type>. If there are multiple LDs of the same '@type' this function
        returns a list instead of a dictionary.

        :param ld_type: The key to search for
        :param default: The returned default if <key> is not found, default: None
        :return: The reached value or <default>
        """
        global _displayed_deprecation_info

        if not _displayed_deprecation_info:
            _displayed_deprecation_info = True
            basic_logger.warning(
                "LinkedDate.get() will be deprecated in the future. Use .get_value_by_key_path() "
                "or .bf_search() instead"
            )
        return self.__dict__.get(ld_type, default)

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

    def bf_search(self, key: str, depth: Optional[int] = None, default: Any = None) -> Optional[Any]:
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
                return None
            else:
                new: List[Dict[str, Any]] = []
                for node in nodes:
                    if isinstance(node, list):
                        new.extend(node)
                        continue
                    elif value := node.get(key):
                        return value
                    new.extend(v for v in node.values() if isinstance(v, dict))
                return search_recursive(new, current_depth + 1) if new else None

        return search_recursive([self.__dict__], 0) or default

    def __repr__(self):
        return f"LD containing '{', '.join(content)}'" if (content := self.__dict__.keys()) else "Empty LD"


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
    """Base class to traverse and build trees of TextSequence.

    The ClassVar __transformation__ is needed to serialize the tree. There must be an entry with type
    Tuple[Callable, Callable] for each field with the first callable beeing the serialization and
    the second the deserialization of that specific field.

    Examples:
        >>> import datetime
        >>> class Tree(TextSequenceTree):
        >>>     head: TextSequence
        >>>     tail: TextSequence
        >>>
        >>>     __transformation__ = {"head": (list, TextSequence), "tail": (list, TextSequence)}


    """

    __transformation__: ClassVar[Dict[str, Tuple[Callable[[Any], Any], Callable[[Any], Any]]]]

    def as_text_sequence(self) -> TextSequence:
        texts = [text for tl in self.df_traversal() for text in tl]
        return TextSequence(texts)

    def text(self, join_on: str = "\n\n", strip_text: bool = True) -> str:
        if strip_text:
            striped_texts = [" ".join(text.split()) for text in self.as_text_sequence()]
            return join_on.join(striped_texts)
        else:
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

    def serialize(self) -> Dict[str, Any]:
        serialized = {}
        for field in fields(self):
            name = field.name
            serialized[name] = self.__transformation__[name][0](getattr(self, name))
        return serialized

    @classmethod
    def deserialize(cls, obj: Dict[str, Any]) -> "TextSequenceTree":
        kwargs = {}
        for name, value in obj.items():
            kwargs[name] = cls.__transformation__[name][1](value)
        # noinspection PyArgumentList
        return cls(**kwargs)

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

    __transformation__ = {"headline": (list, TextSequence), "paragraphs": (list, TextSequence)}


@dataclass
class ArticleBody(TextSequenceTree):
    summary: TextSequence
    sections: List[ArticleSection]

    __transformation__ = {
        "summary": (list, TextSequence),
        "sections": (
            lambda sections: [section.serialize() for section in sections],
            lambda sections: [ArticleSection.deserialize(section) for section in sections],
        ),
    }
