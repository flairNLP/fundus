from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .nine_news import NineNewsParser
from .west_australian import WestAustralianParser


class AU(metaclass=PublisherGroup):
    NineNews = Publisher(
        name="Nine News",
        domain="https://www.9news.com.au/",
        parser=NineNewsParser,
        sources=[
            RSSFeed("https://www.9news.com.au/rss", languages={"en"}),
            Sitemap(
                "https://www.9news.com.au/sitemap.xml",
                sitemap_filter=inverse(regex_filter("sitemap-content-")),
                languages={"en"},
            ),
        ],
    )

    WestAustralian = Publisher(
        name="The West Australian",
        domain="https://thewest.com.au/",
        parser=WestAustralianParser,
        sources=[
            RSSFeed("https://thewest.com.au/rss", languages={"en"}),
            NewsMap("https://thewest.com.au/news-sitemap.xml", languages={"en"}),
            Sitemap("https://thewest.com.au/sitemap.xml", reverse=True, languages={"en"}),
        ],
    )
