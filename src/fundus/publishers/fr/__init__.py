from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.url import NewsMap, Sitemap

from ..shared import EuronewsParser
from .le_figaro import LeFigaroParser
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

    EuronewsFR = PublisherSpec(
        name="Euronews (FR)",
        domain="https://fr.euronews.com/",
        sources=[
            Sitemap("https://fr.euronews.com/sitemaps/fr/articles.xml"),
            NewsMap("https://fr.euronews.com/sitemaps/fr/latest-news.xml"),
        ],
        parser=EuronewsParser,
    )

    LeFigaro = PublisherSpec(
        name="Le Figaro",
        domain="https://www.lefigaro.fr/",
        sources=[
            Sitemap("https://sitemaps.lefigaro.fr/lefigaro.fr/articles.xml"),
            NewsMap("https://www.lefigaro.fr/sitemap_news.xml"),
        ],
        parser=LeFigaroParser,
    )
