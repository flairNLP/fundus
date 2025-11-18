from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.za.daily_maverick import DailyMaverickParser
from fundus.publishers.za.dizindaba import DizindabaParser
from fundus.publishers.za.times_live import TimesLiveParser
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap


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
            RSSFeed("https://www.timeslive.co.za/arc/outboundfeeds/google-news-feed/"),
            NewsMap("https://www.timeslive.co.za/arc/outboundfeeds/sitemap-news-index/"),
            Sitemap("https://www.timeslive.co.za/arc/outboundfeeds/sitemap-index/"),
            Sitemap("https://www.timeslive.co.za/arc/outboundfeeds/sitemap-section-index/"),
        ],
    )

    Dizindaba = Publisher(
        name="Dizindaba",
        domain="https://www.dizindaba.co.za/",
        parser=DizindabaParser,
        sources=[
            Sitemap(
                "https://dizindaba.co.za/sitemap_index.xml",
                sitemap_filter=inverse(regex_filter("post-sitemap")),
                languages={"xh"},
                reverse=True,
            )
        ],
    )
