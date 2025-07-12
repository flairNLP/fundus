from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .derstandard import DerStandardParser
from .die_presse import DiePresseParser
from .kleine_zeitung import KleineZeitungParser
from .orf import OrfParser
from .salzburger_nachrichten import SalzburgerNachrichtenParser

# noinspection PyPep8Naming


class AT(metaclass=PublisherGroup):
    default_language = "de"

    DerStandard = Publisher(
        name="Der Standard",
        domain="https://derstandard.at",
        parser=DerStandardParser,
        sources=[
            RSSFeed("https://www.derstandard.at/rss"),
            NewsMap("https://www.derstandard.at/sitemaps/news.xml"),
            Sitemap("https://www.derstandard.at/sitemaps/sitemap.xml"),
        ],
        request_header={"user-agent": "Googlebot"},
    )

    DiePresse = Publisher(
        name="Die Presse",
        domain="https://diepresse.com",
        parser=DiePresseParser,
        sources=[
            NewsMap("https://www.diepresse.com/news-sitemap"),
        ],
    )

    KleineZeitung = Publisher(
        name="Kleine Zeitung",
        domain="https://www.kleinezeitung.at",
        parser=KleineZeitungParser,
        sources=[
            NewsMap("https://www.kleinezeitung.at/news-sitemap"),
            Sitemap("https://www.kleinezeitung.at/sitemaps/sitemap_main.xml", reverse=True),
        ],
    )

    ORF = Publisher(
        name="Österreichischer Rundfunk",
        domain="https://www.orf.at",
        parser=OrfParser,
        sources=[RSSFeed("https://rss.orf.at/news.xml")],
    )

    SalzburgerNachrichten = Publisher(
        name="Salzburger Nachrichten",
        domain="https://www.sn.at",
        parser=SalzburgerNachrichtenParser,  # Placeholder for future parser
        sources=[
            NewsMap("https://www.sn.at/sitemap/2/0001.xml"),
            Sitemap("https://www.sn.at/sitemapindex.xml", reverse=True),
        ],
    )
