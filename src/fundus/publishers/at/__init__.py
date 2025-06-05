from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .derstandard import DerStandardParser
from .die_presse import DiePresseParser
from .orf import OrfParser

# noinspection PyPep8Naming


class AT(metaclass=PublisherGroup):
    default_language = "de"

    ORF = Publisher(
        name="Österreichischer Rundfunk",
        domain="https://www.orf.at",
        parser=OrfParser,
        sources=[RSSFeed("https://rss.orf.at/news.xml")],
    )

    DiePresse = Publisher(
        name="Die Presse",
        domain="https://diepresse.com",
        parser=DiePresseParser,  # Assuming a parser is defined elsewhere
        sources=[
            NewsMap("https://www.diepresse.com/news-sitemap"),
        ],
    )

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
