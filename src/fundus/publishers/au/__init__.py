from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .nine_news import NineNewsParser
from .west_australian import WestAustralianParser


class AU(metaclass=PublisherGroup):
    default_language = "en"

    NineNews = Publisher(
        name="Nine News",
        domain="https://www.9news.com.au/",
        parser=NineNewsParser,
        sources=[
            RSSFeed("https://www.9news.com.au/rss"),
            Sitemap(
                "https://www.9news.com.au/sitemap.xml",
                sitemap_filter=inverse(regex_filter("sitemap-content-")),
            ),
        ],
    )

    WestAustralian = Publisher(
        name="The West Australian",
        domain="https://thewest.com.au/",
        parser=WestAustralianParser,
        sources=[
            RSSFeed("https://thewest.com.au/rss"),
            NewsMap("https://thewest.com.au/news-sitemap.xml"),
            Sitemap("https://thewest.com.au/sitemap.xml", reverse=True),
        ],
    )
