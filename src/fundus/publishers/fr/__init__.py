from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from ..shared import EuronewsParser
from .le_figaro import LeFigaroParser
from .le_monde import LeMondeParser
from .les_echos import LesEchosParser


class FR(metaclass=PublisherGroup):
    LeMonde = Publisher(
        name="Le Monde",
        domain="https://www.lemonde.fr/",
        parser=LeMondeParser,
        sources=[
            Sitemap("https://www.lemonde.fr/sitemap_index.xml", languages={"fr"}),
            NewsMap("https://www.lemonde.fr/sitemap_news.xml", languages={"fr"}),
        ],
    )

    EuronewsFR = Publisher(
        name="Euronews (FR)",
        domain="https://fr.euronews.com/",
        parser=EuronewsParser,
        sources=[
            Sitemap("https://fr.euronews.com/sitemaps/fr/articles.xml", languages={"fr"}),
            NewsMap("https://fr.euronews.com/sitemaps/fr/latest-news.xml", languages={"fr"}),
        ],
    )

    LeFigaro = Publisher(
        name="Le Figaro",
        domain="https://www.lefigaro.fr/",
        parser=LeFigaroParser,
        sources=[
            Sitemap("https://sitemaps.lefigaro.fr/lefigaro.fr/articles.xml", languages={"fr"}),
            NewsMap("https://www.lefigaro.fr/sitemap_news.xml", languages={"fr"}),
            RSSFeed("https://www.lefigaro.fr/rss/figaro_actualites.xml", languages={"fr"}),
            RSSFeed("https://www.lefigaro.fr/rss/figaro_flash-actu.xml", languages={"fr"}),
        ],
    )

    LesEchos = Publisher(
        name="Les Échos",
        domain="https://www.lesechos.fr/",
        parser=LesEchosParser,
        sources=[
            Sitemap("https://sitemap.lesechos.fr/sitemap_index.xml", reverse=True, languages={"fr"}),
            NewsMap("https://www.lesechos.fr/sitemap_news.xml", languages={"fr"}),
        ],
        deprecated=True,
    )
