from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import Sitemap

from .daily_news_tz import DailyNewsTZParser


class TZ(metaclass=PublisherGroup):
    default_language = "sw"

    DailyNewsTZ = Publisher(
        name="Daily News (Tanzania)",
        domain="https://www.dailynews.co.tz/",
        parser=DailyNewsTZParser,
        sources=[
            Sitemap(
                "https://dailynews.co.tz/wp-sitemap.xml",
                sitemap_filter=inverse(regex_filter("sitemap-posts-post")),
                reverse=True,
                languages={"en"},
            ),
        ],
    )
    HabariLeo = Publisher(
        name="Habari Leo",
        domain="https://www.habarileo.co.tz/",
        parser=DailyNewsTZParser,
        sources=[
            Sitemap(
                "https://habarileo.co.tz/wp-sitemap.xml",
                sitemap_filter=inverse(regex_filter("sitemap-posts-post")),
                reverse=True,
            ),
        ],
    )
