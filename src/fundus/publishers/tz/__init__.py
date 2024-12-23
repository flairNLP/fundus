from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.shared.daily_news_tz import DailyNewsTZParser
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

class TZ(metaclass=PublisherGroup):
    DailyNewsTZ = Publisher(
        name="Daily News (Tanzania)",
        domain="https://www.dailynews.co.tz/",
        parser=DailyNewsTZParser,
        sources=[
            Sitemap(
                "https://www.dailynews.co.tz/sitemap_index.xml",
                sitemap_filter=inverse(regex_filter("post-sitemap")),
                reverse=True,
            ),
        ],
    )
    HabariLeo = Publisher(
        name="Habari Leo",
        domain="https://www.habarileo.co.tz/",
        parser=DailyNewsTZParser,
        sources=[
            Sitemap(
                "https://www.habarileo.co.tz/sitemap_index.xml",
                sitemap_filter=inverse(regex_filter("post-sitemap")),
                reverse=True,
            ),
        ],
    )
