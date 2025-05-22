from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.za.daily_maverick import DailyMaverickParser
from fundus.publishers.za.times_live import TimesLiveParser
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, Sitemap


class ZA(metaclass=PublisherGroup):
    default_language = "en"

    DailyMaverick = Publisher(
        name="Daily Maverick",
        domain="https://www.dailymaverick.co.za/",
        parser=DailyMaverickParser,
        sources=[
            NewsMap("https://www.dailymaverick.co.za/news-sitemap.xml"),
            Sitemap(
                "https://www.dailymaverick.co.za/sitemap_index.xml",
                sitemap_filter=inverse(regex_filter("article-sitemap")),
            ),
        ],
    )

    TimesLive = Publisher(
        name="Times Live",
        domain="https://www.timeslive.co.za/",
        parser=TimesLiveParser,
        sources=[
            NewsMap("https://www.timeslive.co.za/sitemap/google-news/times-live/news/"),
            NewsMap("https://www.timeslive.co.za/sitemap/google-news/times-live/politics/"),
            NewsMap("https://www.timeslive.co.za/sitemap/google-news/times-live/sport/"),
            NewsMap("https://www.timeslive.co.za/sitemap/google-news/times-live/lifestyle/"),
            NewsMap("https://www.timeslive.co.za/sitemap/google-news/sunday-times/news/"),
            NewsMap("https://www.timeslive.co.za/sitemap/google-news/sunday-times/business/"),
            NewsMap("https://www.timeslive.co.za/sitemap/google-news/sunday-times-daily/news/"),
        ],
    )
