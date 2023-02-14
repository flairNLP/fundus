import itertools
from abc import ABC, abstractmethod
from collections.abc import Iterable
from datetime import datetime
from enum import Enum
from typing import Iterator, List
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import feedparser
import lxml.html
import requests

from src.crawler.articles import ArticleSource


def parse_robots(url: str) -> RobotFileParser:
    parsed_url = urlparse(url)
    robots_link = url[:len(url) - len(parsed_url.path)] + '/robots.txt'
    rp = RobotFileParser(robots_link)
    rp.read()
    return rp


class Source(Iterable, ABC):

    @abstractmethod
    def __iter__(self) -> Iterator[ArticleSource]:
        raise NotImplementedError(
            "Every subclass of class 'Source' has to implement __iter__ -> Iterator[ArticleSource]")


class WebSource(Source, ABC):

    @abstractmethod
    def fetch_links(self) -> Iterator[str]:
        raise NotImplementedError


class RSSSource(WebSource):

    def __init__(self, url: str, autodetect: bool = True):
        self.url = url
        self.autodetect = autodetect

    def fetch_links(self):
        rss_feed = feedparser.parse(self.url)
        return [entry["link"] for entry in rss_feed['entries']]

    def __iter__(self) -> Iterator[ArticleSource]:
        with requests.Session() as session:
            for url in self.fetch_links():
                response = session.get(url=url)
                article_source = ArticleSource(url=response.url,
                                               html=response.text,
                                               crawl_date=datetime.now(),
                                               source=self.__class__.__name__)
                yield article_source


class SitemapSource(WebSource):

    def __init__(self, sitemap: str, recursive: bool = True, reverse: bool = False):

        self.sitemap = sitemap
        self.recursive = recursive
        self.reverse = reverse

    def fetch_links(self) -> Iterator[str]:

        def yield_recursive(url: str):
            sitemap_html = session.get(url).content
            if not sitemap_html:
                return
            tree = lxml.html.fromstring(sitemap_html)
            urls = [node.text_content() for node in tree.cssselect('url > loc')]
            yield from reversed(urls) if self.reverse else urls
            if self.recursive:
                sitemap_locs = [node.text_content() for node in tree.cssselect('sitemap > loc')]
                for loc in reversed(sitemap_locs) if self.reverse else sitemap_locs:
                    yield from yield_recursive(loc)

        with requests.Session() as session:
            yield from yield_recursive(self.sitemap)

    def __iter__(self) -> Iterator[ArticleSource]:
        with requests.Session() as session:
            for url in self.fetch_links():
                response = session.get(url=url)
                article_source = ArticleSource(url=response.url,
                                               html=response.text,
                                               crawl_date=datetime.now(),
                                               source=self.__class__.__name__)
                yield article_source


class SitemapSelection(Enum):
    FIRST_ONLY = 1
    NEWS_ONLY = 2
    NO_NEWS = 3
    ALL = 4


class AutoSitemapSource(WebSource):

    def __init__(self, domain: str, recursive: bool = True, reverse: bool = False,
                 sitemap_selection: SitemapSelection = SitemapSelection.ALL):
        self.domain = domain
        self.robots = parse_robots(domain)
        self.selection = sitemap_selection

        for sitemap in self.robots.site_maps():
            test = self._is_news_sitemap(sitemap)

        sitemaps = self.robots.site_maps() or []
        if sitemap_selection == SitemapSelection.FIRST_ONLY:
            valid_sitemaps = sitemaps[0] if sitemaps else []
        elif sitemap_selection == SitemapSelection.NEWS_ONLY:
            valid_sitemaps = [s for s in sitemaps if 'google-news-sitemap' in s]
        elif sitemap_selection == SitemapSelection.NO_NEWS:
            valid_sitemaps = [s for s in sitemaps if 'google-news-sitemap' not in s]
        elif sitemap_selection == SitemapSelection.ALL:
            valid_sitemaps = sitemaps
        else:
            raise ValueError

        self.sitemaps: List[SitemapSource] = [SitemapSource(s, recursive, reverse) for s in valid_sitemaps]

    def _is_news_sitemap(self, url: str) -> bool:
        sitemap = url
        with requests.Session() as session:
            while sitemap:
                html = session.get(sitemap).content
                tree = lxml.html.fromstring(html)
                test = tree.xpath('string(namespace-uri(.))')
                print(test)

    def fetch_links(self) -> Iterator[str]:
        for source in self.sitemaps:
            yield from source.fetch_links()

    def __iter__(self):
        yield from itertools.chain(*self.sitemaps)
