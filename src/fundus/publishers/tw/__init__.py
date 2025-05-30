from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.tw.taipei_times import TaipeiTimesParser
from fundus.scraping.url import NewsMap, Sitemap


class TW(metaclass=PublisherGroup):
    default_language = "tw"

    TaipeiTimes = Publisher(
        name="Taipei Times",
        domain="https://www.taipeitimes.com/",
        parser=TaipeiTimesParser,
        sources=[
            Sitemap("https://www.taipeitimes.com/sitemapIndex.xml", languages={"en"}),
            NewsMap("https://www.taipeitimes.com/sitemap/sitemap.xml", languages={"en"}),
        ],
    )
