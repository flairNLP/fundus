from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.url import RSSFeed

from .orf import OrfParser
from .derstandard import DerStandardParser
# noinspection PyPep8Naming


class AT(PublisherEnum):
    ORF = PublisherSpec(
        name="Österreichischer Rundfunk",
        domain="https://www.orf.at",
        sources=[RSSFeed("https://rss.orf.at/news.xml")],
        parser=OrfParser,
    )

    DerStandard = PublisherSpec(
        name="Der Standard",
        domain="https://derstandard.at",
        sources=[RSSFeed("https://www.derstandard.at/rss")],
        parser=DerStandardParser,
    )
