from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Any, Dict, Iterator, List, Optional, Type

from fundus.parser import BaseParser
from fundus.scraping.scraper import ArticleClassifier
from fundus.scraping.source_url import SourceUrl, RSSFeed, Sitemap, NewsMap


@dataclass(frozen=True)
class PublisherSpec:
    domain: str
    parser: Type[BaseParser]

    article_classifier: Optional[ArticleClassifier] = field(default=None)
    sources: List[SourceUrl] = field(default_factory=list)

    def __post_init__(self):
        if not self.sources:
            raise ValueError("Publishers must at least define either an rss-feed, sitemap or news_map to crawl")


@unique
class PublisherEnum(Enum):
    def __new__(cls, *args, **kwargs):
        value = len(cls.__members__) + 1
        obj = object.__new__(cls)
        obj._value_ = value
        return obj

    def __init__(self, spec: PublisherSpec):
        if not isinstance(spec, PublisherSpec):
            raise ValueError("Your only allowed to generate 'PublisherEnum's from 'PublisherSpec")
        self.domain = spec.domain
        self.parser = spec.parser
        self.article_classifier = spec.article_classifier
        self.sources = spec.sources

    def supports(self, source_type: Optional[str]) -> bool:
        if source_type == "rss":
            return bool([el for el in self.sources if type(el) == RSSFeed])
        elif source_type == "sitemap":
            return bool([el for el in self.sources if type(el) == Sitemap])
        elif source_type == "news":
            return bool([el for el in self.sources if type(el) == NewsMap])
        elif source_type is None:
            return True
        else:
            raise ValueError(f"Unsupported value {source_type} for parameter <source_type>")

    @classmethod
    def search(cls, attrs: Optional[List[str]] = None, source_type: Optional[str] = None) -> List["PublisherEnum"]:
        assert attrs or source_type, "You have to define at least one search condition"
        if not attrs:
            attrs = []
        matched = []
        attrs_set = set(attrs)
        spec: PublisherEnum
        for spec in list(cls):
            if attrs_set.issubset(spec.parser.attributes().names) and spec.supports(source_type):
                matched.append(spec)
        return matched

    def __get__(self, instance, owner):
        return self


class CollectionMeta(type):
    @property
    def _members(cls) -> Dict[str, Any]:
        return {name: obj for name, obj in cls.__dict__.items() if "__" not in name}

    def __contains__(cls, __x: object) -> bool:
        return __x in cls._members.values()

    def __iter__(cls) -> Iterator[PublisherEnum]:
        for coll in cls._members.values():
            yield from coll

    def __len__(cls) -> int:
        return len(cls._members)
