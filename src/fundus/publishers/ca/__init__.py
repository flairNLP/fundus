from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.ca.cbc_news import CBCNewsParser
from fundus.publishers.ca.globe_and_mail import TheGlobeAndMailParser
from fundus.publishers.ca.national_post import NationalPostParser
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

# noinspection PyPep8Naming


class CA(metaclass=PublisherGroup):
    default_language = "en"

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
    TheGlobeAndMail = Publisher(
        name="The Globe and Mail",
        domain="https://www.theglobeandmail.com",
        parser=TheGlobeAndMailParser,
        sources=[
            NewsMap("https://www.theglobeandmail.com/arc/outboundfeeds/news-sitemap-index/?outputType=xml"),
            NewsMap("https://www.theglobeandmail.com/arc/outboundfeeds/sitemap-index/?outputType=xml"),
        ],
    )

    NationalPost = Publisher(
        name="National Post",
        domain="https://nationalpost.com",
        parser=NationalPostParser,
        sources=[
            NewsMap("https://nationalpost.com/sitemap-news.xml"),
            Sitemap("https://nationalpost.com/sitemap-old.xml"),
            RSSFeed("https://nationalpost.com/feed"),
        ],
    )
