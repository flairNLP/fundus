import json
from abc import ABC
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, List


@dataclass(frozen=True)
class BaseArticle(ABC):
    url: str
    html: str
    crawl_date: datetime

    def serialize(self) -> dict[str, Any]:
        return self.__dict__

    @classmethod
    def deserialize(cls, serialized: dict[str, Any]):
        return cls(**serialized)

    def pprint(self, indent: int = 4, ensure_ascii: bool = False, default: Callable[[Any], Any] = str,
               exclude: List[str] = None) -> str:
        to_serialize: dict[str, Any] = self.__dict__.copy()
        for key in exclude:
            if not hasattr(self, key):
                raise AttributeError(f"Tried to exclude key '{key} which isn't present in this'{self}' instance")
            to_serialize.pop(key)
        return json.dumps(to_serialize, indent=indent, ensure_ascii=ensure_ascii, default=default)


@dataclass(frozen=True)
class ArticleSource(BaseArticle):
    source: str


@dataclass(frozen=True)
class Article(BaseArticle):
    extracted: dict[str, Any]
    exception: Exception = None
    source: str = None

    # TODO: discuss if we want to be straight frozen here or update for dot access
    def update(self, data: dict[str, Any]) -> None:
        self.__dict__.update(data)

    @property
    def complete(self) -> bool:
        return all(not (isinstance(attr, Exception) or attr is None) for attr in self.extracted.values())
