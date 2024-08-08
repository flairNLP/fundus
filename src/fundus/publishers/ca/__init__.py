from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.ca.cbc_news import CBCNewsParser
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

# noinspection PyPep8Naming


class CA(metaclass=PublisherGroup):
    CBCNews = Publisher(
        name="CBC News",
        domain="https://www.cbc.ca/",
        parser=CBCNewsParser,
        sources=[
            RSSFeed("https://www.cbc.ca/webfeed/rss/rss-topstories"),
            RSSFeed("https://www.cbc.ca/webfeed/rss/rss-world"),
            RSSFeed("https://www.cbc.ca/webfeed/rss/rss-canada"),
        ],
    )
