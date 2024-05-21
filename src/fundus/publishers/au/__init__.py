from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import RSSFeed, Sitemap

from .nine_news import NineNewsParser


class AU(metaclass=PublisherGroup):
    NineNews = Publisher(
        name="Nine News",
        domain="https://www.9news.com.au/",
        parser=NineNewsParser,
        sources=[
            RSSFeed("https://www.9news.com.au/rss"),
            Sitemap("https://www.9news.com.au/sitemap.xml", sitemap_filter=inverse(regex_filter("sitemap-content-"))),
        ],
    )
