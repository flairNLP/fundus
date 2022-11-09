from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import datetime
from typing import Iterator, Literal, Type

import feedparser
import lxml.html
import requests

from src.parser.html_parser import BaseParser
from src.pipeline.articles import ArticleSource, Article


class Source(Iterable, ABC):
    domain: str
    url: str

    @abstractmethod
    def __iter__(self) -> Iterator[ArticleSource]:
        raise NotImplemented("Every subclass of class 'Source' has to implement __iter__ -> Iterator[ArticleSource]")


class RSSSource(Source):

    def __init__(self, domain: str, url: str):
        self.domain = domain
        self.url = url

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
                                               source=self.__class__.__name__)
                yield article_source


class SitemapSource(Source):

    def __init__(self, domain: str, url: str):
        self.domain = domain
        self.url = url

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
                                               source=self.__class__.__name__)
                yield article_source
