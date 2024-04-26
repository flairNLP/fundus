from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.filter import regex_filter
from fundus.scraping.url import NewsMap, RSSFeed

from .nine_news import NineNewsParser


class AU(PublisherEnum):
    NineNews = PublisherSpec(
        name="Nine News",
        domain="https://www.9news.com.au/",
        sources=[
            RSSFeed("https://www.9news.com.au/rss"),
            NewsMap(
                "https://www.9news.com.au/sitemap.xml", sitemap_filter=regex_filter("www.9news.com.au/sitemap-content-")
            ),
        ],
        parser=NineNewsParser,
    )
