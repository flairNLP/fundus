from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.cz.seznamzpravy import SeznamZpravyParser
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap


class CZ(metaclass=PublisherGroup):
    default_language = "cs"

    SeznamZpravy = Publisher(
        name="SeznamZpravy",
        domain="https://seznamzpravy.cz/",
        parser=SeznamZpravyParser,
        sources=[
            RSSFeed("https://www.seznamzpravy.cz/rss"),
            Sitemap("https://www.seznamzpravy.cz/sitemaps/sitemap_articles.xml"),
            NewsMap("https://www.seznamzpravy.cz/sitemaps/sitemap_news.xml"),
        ],
    )
