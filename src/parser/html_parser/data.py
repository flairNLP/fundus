from abc import ABC
from dataclasses import dataclass, fields
from typing import (
    Any,
    Collection,
    Dict,
    Iterable,
    Iterator,
    List,
    Optional,
    Sequence,
    Tuple,
    overload,
)

from src.logging.logger import basic_logger

_displayed_deprecation_info = False


class LinkedData:
    def __init__(self, lds: Iterable[Dict[str, Any]] = ()):
        self._ld_by_type: Dict[str, Dict[str, Any]] = {}
        for ld in lds:
            if ld_type := ld.get("@type"):
                self._ld_by_type[ld_type] = ld
            else:
                raise ValueError(f"Found no type for LD")

        for name, ld in sorted(self._ld_by_type.items(), key=lambda t: t[0]):
            self.__dict__[name] = ld

        self._contains = [ld_type for ld_type in self._ld_by_type.keys() if ld_type is not None]

    def get(self, key: str, default: Any = None):
        """
        This function acts like get() on pythons Mapping type with the difference that this method will
        iterate through all found ld types and return the first value where <key> matches. If no match occurs,
        <default> will be returned.

        If there is a ld without a type, thins methode will raise a NotImplementedError

        :param key: The key to search vor
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
        for name, ld in sorted(self._ld_by_type.items(), key=lambda t: t[0]):
            if not name:
                raise NotImplementedError("Currently this function does not support lds without types")
            elif value := ld.get(key):
                return value
        return default

    def get_value_by_key_path(self, key_path: List[str], default: Any = None):
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
        tmp = self._ld_by_type.copy()
        for key in key_path:
            if not (nxt := tmp.get(key)):
                return default
            tmp = nxt
        return tmp

    def bf_search(self, key: str, depth: Optional[int] = None) -> Any:
        """
        This is a classic BF search on the nested dicts representing the JSON-LD. <key> specifies the dict key to
        search, <depth> the depth level. If the depth level is set to None, this method will search through the whole
        LD. It is important to notice that this will  only return the value of the first matched key.
        For more precise operations consider using get() or get_by_key_path().

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

        def search_recursive(nodes: Iterable[Dict[str, Any]], current_depth: int):
            if current_depth == depth:
                return None
            else:
                new: List[Dict[str, Any]] = []
                for node in nodes:
                    if value := node.get(key):
                        return value
                    new.extend(v for v in node.values() if isinstance(v, dict))
                return search_recursive(new, current_depth + 1) if new else None

        return search_recursive(self._ld_by_type.values(), 0)

    def __repr__(self):
        return f"LD containing '{', '.join(content)}'" if (content := self._contains) else "Empty LD"


class TextSequence(Sequence[str]):
    def __init__(self, texts: Iterable[str]):
        self._data: Tuple[str, ...] = tuple(texts)

    def text(self, join_on: str = "\n") -> str:
        return join_on.join(self)

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


@dataclass
class TextSequenceTree(ABC):
    def as_text_sequence(self) -> TextSequence:
        texts = [text for tl in self.df_traversal() for text in tl]
        return TextSequence(texts)

    def text(self, join_on: str = "\n\n") -> str:
        return self.as_text_sequence().text(join_on)

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

    def __iter__(self):
        field_values = [getattr(self, f.name) for f in fields(self)]
        yield from field_values

    def __str__(self):
        return self.text()


@dataclass
class ArticleSection(TextSequenceTree):
    headline: TextSequence
    paragraphs: TextSequence


@dataclass
class ArticleBody(TextSequenceTree):
    summary: TextSequence
    sections: List[ArticleSection]
