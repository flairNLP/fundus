from fundus.publishers.base_objects import PublisherGroup, Publisher
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .derstandard import DerStandardParser
from .orf import OrfParser

# noinspection PyPep8Naming


class AT(PublisherGroup):
    ORF = Publisher(
        name="Österreichischer Rundfunk",
        domain="https://www.orf.at",
        sources=[RSSFeed("https://rss.orf.at/news.xml")],
        parser=OrfParser,
    )

    DerStandard = Publisher(
        name="Der Standard",
        domain="https://derstandard.at",
        sources=[
            RSSFeed("https://www.derstandard.at/rss"),
            NewsMap("https://www.derstandard.at/sitemaps/news.xml"),
            Sitemap("https://www.derstandard.at/sitemaps/sitemap.xml"),
        ],
        request_header={"user-agent": "Googlebot"},
        parser=DerStandardParser,
    )
