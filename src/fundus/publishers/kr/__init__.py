from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, Sitemap

from .hankook_ilbo import HankookIlboParser
from .mbn import MBNParser


class KR(metaclass=PublisherGroup):
    default_language = "ko"

    MBN = Publisher(
        name="Maeil Business Newspaper",
        domain="https://www.mk.co.kr/",
        parser=MBNParser,
        sources=[
            # RSSFeed("https://www.mk.co.kr/rss/40300001/"),
            Sitemap(
                "https://www.mk.co.kr/sitemap/latest-articles/",
                sitemap_filter=inverse(regex_filter(r"/news/columnists/")),
            ),
            Sitemap(
                "https://www.mk.co.kr/sitemap/daily-articles/",
                sitemap_filter=inverse(regex_filter(r"/news/columnists/")),
            ),
        ],
    )

    HankookIlbo = Publisher(
        name="Hankook Ilbo",
        domain="https://www.hankookilbo.com/",
        parser=HankookIlboParser,
        sources=[
            NewsMap("https://www.hankookilbo.com/sitemap/latest-articles"),
            Sitemap("https://www.hankookilbo.com/sitemap/daily-articles/2020"),
        ],
    )
