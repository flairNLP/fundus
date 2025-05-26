from fundus.publishers.base_objects import PublisherGroup, Publisher
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .jtbc import JTBCParser

class KR(metaclass=PublisherGroup):
    default_language = "kr"

    JTBC = Publisher(
            name="JTBC",
            domain="https://jtbc.co.kr/",
            parser=JTBCParser,
            sources=[
                RSSFeed(url="http://fs.jtbc.joins.com/RSS/newsflash.xml"),
                RSSFeed(url="http://fs.jtbc.joins.com/RSS/politics.xml"),
                RSSFeed(url="http://fs.jtbc.joins.com/RSS/economy.xml"),
                RSSFeed(url="http://fs.jtbc.joins.com/RSS/society.xml"),
                RSSFeed(url="http://fs.jtbc.joins.com/RSS/international.xml"),
                RSSFeed(url="http://fs.jtbc.joins.com/RSS/culture.xml"),
                RSSFeed(url="http://fs.jtbc.joins.com/RSS/entertainment.xml"),
                RSSFeed(url="http://fs.jtbc.joins.com/RSS/sports.xml"),
                RSSFeed(url="http://fs.jtbc.joins.com/RSS/newsroom.xml"),
                RSSFeed(url="http://fs.jtbc.joins.com/RSS/ranking.xml"),
                Sitemap("https://jtbc.co.kr/sitemap/index_sitemap.xml"),
            ]
        )

