from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.za.times_live import TimesLiveParser
from fundus.scraping.url import NewsMap, Sitemap


class ZA(metaclass=PublisherGroup):
    default_language = "en"

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
