from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, fields
from typing import (
    Any,
    Collection,
    Dict,
    Iterable,
    Iterator,
    List,
    Sequence,
    Tuple,
    overload,
)

from typing_extensions import Self


class TextSequence(Sequence[str]):
    def __init__(self, texts: Iterable[str]):
        self._data: Tuple[str, ...] = tuple(texts)

    @overload
    def __getitem__(self, i: int) -> str: ...

    @overload
    def __getitem__(self, s: slice) -> "TextSequence": ...

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
