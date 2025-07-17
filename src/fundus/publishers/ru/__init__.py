from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .kommersant import KommersantParser


class RU(metaclass=PublisherGroup):
    default_language = "ru"

    Kommersant = Publisher(
        name="Kommersant",
        domain="https://www.kommersant.ru/",
        parser=KommersantParser,
        sources=[
            RSSFeed("https://www.kommersant.ru/RSS/news.xml"),
            Sitemap(
                "https://www.kommersant.ru/sitemaps/all_docs_sitemap.xml",
                reverse=True,
            ),
            NewsMap("https://www.kommersant.ru/sitemaps/sitemap_news.xml"),
        ],
        suppress_robots=True,
    )
