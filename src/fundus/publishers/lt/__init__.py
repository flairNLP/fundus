from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.url import RSSFeed, Sitemap

from .lrt import LRTParser

# noinspection PyPep8Naming


class LT(PublisherEnum):
    LRT = PublisherSpec(
        name="Lithuanian National Radio and Television",
        domain="https://www.lrt.lt",
        sources=[Sitemap("https://www.lrt.lt/servisai/sitemap/sitemap-index.xml"), RSSFeed("https://www.lrt.lt/?rss")],
        parser=LRTParser,
    )
