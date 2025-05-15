from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.url import NewsMap, Sitemap

from .hankook_ilbo import HankookIlboParser


class KR(metaclass=PublisherGroup):
    default_language = "ko"

    HankookIlbo = Publisher(
        name="Hankook Ilbo",
        domain="https://www.hankookilbo.com/",
        parser=HankookIlboParser,
        sources=[
            NewsMap("https://www.hankookilbo.com/sitemap/latest-articles"),
            Sitemap("https://www.hankookilbo.com/sitemap/daily-articles/2020"),
        ],
    )
