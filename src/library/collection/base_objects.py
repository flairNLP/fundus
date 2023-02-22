from dataclasses import dataclass, field
from enum import Enum, unique
from typing import Type, List, Optional, Tuple
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import more_itertools
import requests
from lxml import etree
from lxml.etree import Element

from src.parser.html_parser import BaseParser


def parse_robots(url: str) -> RobotFileParser:
    parsed_url = urlparse(url)
    robots_link = url[:len(url) - len(parsed_url.path)] + '/robots.txt'
    rp = RobotFileParser(robots_link)
    rp.read()
    return rp


def resolve_sitemaps(domain: str) -> Tuple[List[str], ...]:
    with requests.Session() as session:
        def is_news_sitemap(url: str) -> bool:
            remaining_depth = 30
            while url:
                if remaining_depth == 0:
                    raise RecursionError('Exceeded recursion depth')
                remaining_depth -= 1
                html: bytes = session.get(url).content
                root: Element = etree.fromstring(html)
                if new := root.cssselect('sitemap > loc'):
                    url = new[0].text
                    continue
                else:
                    return True if root.nsmap.get('news') else False

        robots = parse_robots(domain)
        if not (sitemaps := robots.site_maps()):
            return [], []
        sitemaps, news_maps = more_itertools.partition(is_news_sitemap, set(sitemaps))
        sitemaps = list(sitemaps)
        news_maps = list(news_maps)
        return sitemaps, news_maps


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

        if not (self.sitemaps and self.news_map):
            sitemaps, news_map = resolve_sitemaps(self.domain)
            if not self.sitemaps:
                self.sitemaps = sitemaps
            if not self.news_map:
                assert len(news_map) < 2, f'Found more than one news-map while parsing {self.domain}'
                self.news_map = next(iter(news_map), None)

    def supports(self, source_type: str) -> bool:
        if source_type == 'rss':
            return bool(self.rss_feeds)
        elif source_type == 'sitemap':
            return bool(self.sitemaps)
        elif source_type == 'news':
            return bool(self.news_map)
        elif source_type is None:
            return True

    @classmethod
    def search(cls, attrs: List[str] = None, source_type: str = None) -> List['PublisherEnum']:
        assert attrs or source_type, "You have to define at least one search condition"
        if not attrs:
            attrs = []
        matched = []
        attrs = set(attrs)
        spec: PublisherEnum
        for spec in list(cls):
            if attrs.issubset(spec.parser.attributes()) and spec.supports(source_type):
                matched.append(spec)
        return matched
