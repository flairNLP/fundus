from dataclasses import dataclass, field
from enum import Enum, unique
from typing import List, Optional, Type

from src.logging.logger import basic_logger
from src.parser.html_parser import BaseParser


@dataclass(frozen=True)
class PublisherSpec:
    domain: str
    parser: Type[BaseParser]
    rss_feeds: List[str] = field(default_factory=list)
    sitemaps: List[str] = field(default_factory=list)
    news_map: Optional[str] = field(default=None)

    def __post_init__(self):
        if not (self.rss_feeds or self.sitemaps):
            raise ValueError("Publishers must at least define either an rss-feed or sitemap to crawl")


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
        self.rss_feeds = spec.rss_feeds
        self.sitemaps = spec.sitemaps
        self.news_map = spec.news_map
        self.parser = spec.parser

    def supports(self, source_type: Optional[str]) -> bool:
        if source_type == "rss":
            return bool(self.rss_feeds)
        elif source_type == "sitemap":
            return bool(self.sitemaps)
        elif source_type == "news":
            return bool(self.news_map)
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
            if attrs_set.issubset(spec.parser.attributes()) and spec.supports(source_type):
                matched.append(spec)
        return matched
