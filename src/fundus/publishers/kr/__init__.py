from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.url import RSSFeed, Sitemap

from .mbn import MBNParser


class KR(metaclass=PublisherGroup):
    default_language = "kr"

    MBN = Publisher(
        name="MaeilBusinessNewspaper",
        domain="https://www.mk.co.kr/",
        parser=MBNParser,
        sources=[
            RSSFeed("https://www.mk.co.kr/rss/40300001/"),
            Sitemap("https://www.mk.co.kr/sitemap/latest-articles/"),
        ],
    )
