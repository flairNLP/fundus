from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.tw.taipei_times import TaipeiTimesParser
from fundus.scraping.url import NewsMap, Sitemap, RSSFeed


class TW(metaclass=PublisherGroup):
    default_language = "tw"

    TaipeiTimes = Publisher(
        name="Taipei Times",
        domain="https://www.taipeitimes.com/",
        parser=TaipeiTimesParser,
        sources=[
            RSSFeed("https://www.taipeitimes.com/xml/index.rss", languages={"en"}),
        ],
    )
