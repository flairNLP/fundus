from fundus.publishers.base_objects import PublisherGroup, Publisher
from fundus.scraping.url import RSSFeed, Sitemap

from .lrt import LRTParser

# noinspection PyPep8Naming


class LT(metaclass=PublisherGroup):
    LRT = Publisher(
        name="Lithuanian National Radio and Television",
        domain="https://www.lrt.lt",
        sources=[Sitemap("https://www.lrt.lt/servisai/sitemap/sitemap-index.xml"), RSSFeed("https://www.lrt.lt/?rss")],
        parser=LRTParser,
    )
