import json
from abc import ABC
from abc import abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, List, Dict
from typing import Iterator

import feedparser
import lxml.html
import requests


@dataclass(frozen=True)
class BaseArticle(ABC):
    url: str
    html: str
    crawl_date: datetime
    source: 'Source'

    def serialize(self) -> Dict[str, Any]:
        return self.__dict__

    @classmethod
    def deserialize(cls, serialized: Dict[str, Any]):
        return cls(**serialized)

    def pprint(self, indent: int = 4, ensure_ascii: bool = False, default: Callable[[Any], Any] = str,
               exclude: List[str] = None) -> str:
        to_serialize: Dict[str, Any] = self.__dict__.copy()
        for key in exclude:
            if not hasattr(self, key):
                raise AttributeError(f"Tried to exclude key '{key} which isn't present in this'{self}' instance")
            to_serialize.pop(key)
        return json.dumps(to_serialize, indent=indent, ensure_ascii=ensure_ascii, default=default)


@dataclass(frozen=True)
class ArticleSource(BaseArticle):
    pass


@dataclass(frozen=True)
class Article(BaseArticle):
    extracted: Dict[str, Any]
    exception: Exception = None

    # TODO: discuss if we want to be straight frozen here or update for dot access
    def update(self, data: Dict[str, Any]) -> None:
        self.__dict__.update(data)

    @property
    def complete(self) -> bool:
        return all(not (isinstance(attr, Exception) or attr is None) for attr in self.extracted.values())

    @property
    def publisher(self) -> str:
        return self.source.publisher_name


class Source(Iterable, ABC):
    domain: str
    url: str

    def __init__(self, publisher_name: str, domain: str, url: str):
        self.publisher_name = publisher_name
        self.domain = domain
        self.url = url

    @abstractmethod
    def __iter__(self) -> Iterator[ArticleSource]:
        raise NotImplemented("Every subclass of class 'Source' has to implement __iter__ -> Iterator[ArticleSource]")


class RSSSource(Source):

    def fetch(self):
        rss_feed = feedparser.parse(self.url)
        return [entry["link"] for entry in rss_feed['entries']]

    def __iter__(self) -> Iterator[ArticleSource]:
        with requests.Session() as session:
            for url in self.fetch():
                response = session.get(url=url)
                article_source = ArticleSource(url=response.url,
                                               html=response.text,
                                               crawl_date=datetime.now(),
                                               source=self)
                yield article_source


class SitemapSource(Source):

    def fetch(self) -> Iterator[str]:
        with requests.Session() as session:
            sitemap_html = session.get(self.url)
            sitemap_tree = lxml.html.fromstring(sitemap_html)
            url_nodes = sitemap_tree.cssselect('url > loc')
            sitemap_urls = [node.text_content() for node in url_nodes]
            return sitemap_urls

    def __iter__(self) -> Iterator[ArticleSource]:
        with requests.Session() as session:
            for url in self.fetch():
                response = session.get(url=url)
                article_source = ArticleSource(url=response.url,
                                               html=response.text,
                                               crawl_date=datetime.now(),
                                               source=self)
                yield article_source
