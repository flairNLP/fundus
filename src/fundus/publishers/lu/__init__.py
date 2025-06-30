from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.url import RSSFeed, Sitemap

from .tageblatt import TageblattParser


class LU(metaclass=PublisherGroup):
    default_language = "de"

    Tageblatt = Publisher(
        name="Tagebblatt",
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
        ],
    )
