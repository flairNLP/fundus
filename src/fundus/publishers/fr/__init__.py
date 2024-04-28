from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.url import NewsMap, Sitemap

from .euronews import EuronewsParser
from .le_monde import LeMondeParser


class FR(PublisherEnum):
    LeMonde = PublisherSpec(
        name="Le Monde",
        domain="https://www.lemonde.fr/",
        sources=[
            Sitemap("https://www.lemonde.fr/sitemap_index.xml"),
            NewsMap("https://www.lemonde.fr/sitemap_news.xml"),
        ],
        parser=LeMondeParser,
    )

    Euronews = PublisherSpec(
        name="Euronews",
        domain="https://www.euronews.com/",
        sources=[
            Sitemap("https://www.euronews.com/sitemaps/en/articles.xml"),
            Sitemap("https://de.euronews.com/sitemaps/de/articles.xml"),
            Sitemap("https://fr.euronews.com/sitemaps/fr/articles.xml"),
            NewsMap("https://www.euronews.com/sitemaps/en/latest-news.xml"),
            NewsMap("https://de.euronews.com/sitemaps/de/latest-news.xml"),
            NewsMap("https://fr.euronews.com/sitemaps/fr/latest-news.xml"),
        ],
        parser=EuronewsParser,
    )
