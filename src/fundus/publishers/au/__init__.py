from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .nine_news import NineNewsParser


class AU(PublisherEnum):
    NineNews = PublisherSpec(
        name="Nine News",
        domain="https://www.9news.com.au/",
        sources=[
            RSSFeed("https://www.9news.com.au/rss"),
            Sitemap("https://www.9news.com.au/sitemap.xml", sitemap_filter=inverse(regex_filter("sitemap-content-"))),
        ],
        parser=NineNewsParser,
    )
