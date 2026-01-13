from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .luxemburger_wort import LuxemburgerWortParser
from .tageblatt import TageblattParser


class LU(metaclass=PublisherGroup):
    default_language = "de"

    Tageblatt = Publisher(
        name="Tageblatt",
        domain="https://www.tageblatt.lu/",
        parser=TageblattParser,
        url_filter=regex_filter("-[a-z]+[0-9]+.html"),
        sources=[
            Sitemap(
                "https://www.tageblatt.lu/Sitemap_Index.xml.gz",
                reverse=True,
                sitemap_filter=regex_filter("Sitemap_Nav.xml"),
            ),
        ],
    )

    LuxemburgerWort = Publisher(
        name="Luxemburger Wort",
        domain="https://www.wort.lu/",
        parser=LuxemburgerWortParser,
        sources=[
            RSSFeed("https://www.wort.lu/de/rss"),
            Sitemap("https://www.wort.lu/sitemap.xml", reverse=True),
            NewsMap("https://www.wort.lu/sitemap-news.xml"),
        ],
    )
