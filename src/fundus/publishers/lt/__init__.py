from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.url import RSSFeed, Sitemap

from .lrt import LRTParser

# noinspection PyPep8Naming


class LT(metaclass=PublisherGroup):
    default_language = "lt"

    LRT = Publisher(
        name="Lithuanian National Radio and Television",
        domain="https://www.lrt.lt",
        parser=LRTParser,
        sources=[
            Sitemap("https://www.lrt.lt/servisai/sitemap/sitemap-index.xml"),
            RSSFeed("https://www.lrt.lt/?rss"),
        ],
    )
