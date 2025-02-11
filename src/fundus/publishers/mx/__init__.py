from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.url import Sitemap

from ...scraping.filter import inverse, regex_filter
from .mexico_news_daily import MexicoNewsDailyParser


class MX(metaclass=PublisherGroup):
    MexicoNewsDaily = Publisher(
        name="Mexico News Daily",
        domain="https://mexiconewsdaily.com/",
        parser=MexicoNewsDailyParser,
        sources=[
            Sitemap(
                "https://mexiconewsdaily.com/sitemap_index.xml", sitemap_filter=inverse(regex_filter(r"post-sitemap"))
            )
        ],
    )
