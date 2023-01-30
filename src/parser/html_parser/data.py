from abc import ABC
from collections import defaultdict
from dataclasses import dataclass, fields, field
from typing import List, Iterable, Any, Union, Dict, MutableSequence, overload, get_args, Generic, Collection, get_origin


class LinkedData:
    __slots__ = ['_ld_by_type', '__dict__']

    def __init__(self, lds: List[Dict[str, any]]):
        self._ld_by_type: Dict[str, Union[List[Dict[str, any]], Dict[str, any]]] = defaultdict(list)
        for ld in lds:
            if ld_type := ld.get('@type'):
                self._ld_by_type[ld_type] = ld
            else:
                self._ld_by_type[ld_type].append(ld)

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
            if not (tmp := tmp.get(key)):
                return default
        return tmp

    def bf_search(self, key: str, depth: int = None) -> Any:
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

        def search_recursive(nodes: Iterable[dict], current_depth: int):
            if current_depth == depth:
                return None
            else:
                new = []
                for node in nodes:
                    if isinstance(node, dict) and (value := node.get(key)):
                        return value
                    new.extend(v for v in node.values() if isinstance(v, dict))
                return search_recursive(new, current_depth + 1) if new else None

        return search_recursive(self._ld_by_type.values(), 0)

    def __repr__(self):
        return f"LD containing '{', '.join(self._contains)}'"


# TODO: i wish we could use collections.UserList here but sadly, and i don't understand why, python do not support this
#   wth a type hint
class TextList(MutableSequence[str]):

    def __init__(self, texts: Iterable[str] = None):
        self.data: List[str] = list(texts) if texts else []

    def as_list(self) -> List[str]:
        return [text for text in self.data]

    def insert(self, index: int, value: str) -> None:
        self.data.insert(index, value)

    def text(self, join_on: str = '\n') -> str:
        return join_on.join(self)

    @overload
    def __getitem__(self, i: int) -> str:
        ...

    @overload
    def __getitem__(self, s: slice) -> 'TextList':
        ...

    def __getitem__(self, i):
        if isinstance(i, slice):
            return self.__class__(self.data[i])
        else:
            return self.data[i]

    @overload
    def __setitem__(self, i: int, item: str) -> None:
        ...

    @overload
    def __setitem__(self, s: slice, item: Iterable[str]) -> None:
        ...

    def __setitem__(self, i, item):
        self.data.__setitem__(i, item)

    def __delitem__(self, i: Union[int, slice]) -> None:
        self.data.__delitem__(i)

    def __len__(self) -> int:
        return len(self.data)

    def __iter__(self) -> Iterable[str]:
        return iter(self.data)

    def __repr__(self) -> str:
        return repr(self.data)


@dataclass
class TextTree(ABC):

    def as_ordered_list(self) -> TextList:
        texts = [text for tl in self._iter_text() for text in tl]
        return TextList(texts)

    def text(self, join_on: str = '\n\n') -> str:
        return self.as_ordered_list().text(join_on)

    def _iter_text(self) -> Iterable[TextList]:
        field_values = [getattr(self, field.name) for field in fields(self)]
        for value in field_values:
            if isinstance(value, TextList):
                yield value
            elif isinstance(value, TextTree):
                yield from value._iter_text()
            elif isinstance(value, list):
                for element in value:
                    if isinstance(element, TextTree):
                        yield from element._iter_text()
                    else:
                        raise TypeError(f"only lists of type {TextTree} are allowed as list typed fields "
                                        f"but found value with type {type(value)}")
            else:
                raise TypeError(f"{type(self)} should only consists of fields "
                                f"with type {TextList} or {type(self)} but found value with type {type(value)}")

    @classmethod
    def from_instructions(cls, instructions: tuple) -> 'TextTree':
        kwargs = {}
        for i, dc_field in enumerate(fields(cls)):
            a = get_args(dc_field.type)
            o = get_origin(dc_field.type)
            if o:
                kwargs[dc_field.name] = o([a[0].from_instructions(args) for args in instructions[i]])
            else:
                kwargs[dc_field.name] = dc_field.type(instructions[i])

        return cls(**kwargs)

    def __str__(self):
        return self.text()


@dataclass
class ArticleSection(TextTree):
    headline: TextList
    paragraphs: TextList


@dataclass
class ArticleBody(TextTree):
    summary: TextList
    sections: List[ArticleSection]
