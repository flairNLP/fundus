from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Type, List

from src.parser.html_parser import BaseParser


@dataclass(frozen=True)
class PublisherSpec:
    domain: str
    parser: Type[BaseParser]
    rss_feeds: List[str] = field(default_factory=list)
    sitemaps: List[str] = field(default_factory=list)

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
        self.sitemap = spec.sitemaps
        self.parser = spec.parser

    @classmethod
    def search(cls, attrs: List[str]):
        matched = []
        attrs = set(attrs)
        for spec in list(cls):
            if attrs.issubset(spec.parser.attributes()):
                matched.append(spec)
        return matched
