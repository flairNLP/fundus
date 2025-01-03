from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.tw.TaipeiTimes import TaipeiTimesParser
from fundus.scraping.url import NewsMap, Sitemap


class TW(metaclass=PublisherGroup):
    TaipeiTimes = Publisher(
        name="Taipei Times",
        domain="https://www.taipeitimes.com/",
        parser=TaipeiTimesParser,
        sources=[
            Sitemap(
                "https://www.taipeitimes.com/sitemapIndex.xml",
            ),
            NewsMap("https://www.taipeitimes.com/sitemap/sitemap.xml"),
        ],
    )
