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
        sources=[
            RSSFeed("https://www.tageblatt.lu/category/politik/feed/atom/"),
            RSSFeed("https://www.tageblatt.lu/category/meinung/feed/atom/"),
            RSSFeed("https://www.tageblatt.lu/category/nachrichten/feed/atom/"),
            RSSFeed("https://www.tageblatt.lu/category/wirtschaft/feed/atom/"),
            RSSFeed("https://www.tageblatt.lu/category/sport/feed/atom/"),
            RSSFeed("https://www.tageblatt.lu/category/kultur/feed/atom/"),
            RSSFeed("https://www.tageblatt.lu/category/wissen/feed/atom/"),
            RSSFeed("https://www.tageblatt.lu/category/campus/feed/atom/"),
            RSSFeed("https://www.tageblatt.lu/category/magazin/feed/atom/"),
            RSSFeed("https://www.tageblatt.lu/category/auto/feed/atom/"),
            Sitemap(
                "https://www.tageblatt.lu/wp-sitemap.xml",
                sitemap_filter=inverse(regex_filter("posts-post")),
                reverse=True,
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
