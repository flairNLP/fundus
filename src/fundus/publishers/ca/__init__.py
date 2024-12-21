from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.ca.cbc_news import CBCNewsParser
from fundus.publishers.ca.globe_and_mail import TheGlobeAndMailParser
from fundus.publishers.ca.national_post import NationalPostParser
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

# noinspection PyPep8Naming


class CA(metaclass=PublisherGroup):
    CBCNews = Publisher(
        name="CBC News",
        domain="https://www.cbc.ca/",
        parser=CBCNewsParser,
        sources=[
            RSSFeed("https://www.cbc.ca/webfeed/rss/rss-topstories", languages={"en"}),
            RSSFeed("https://www.cbc.ca/webfeed/rss/rss-world", languages={"en"}),
            RSSFeed("https://www.cbc.ca/webfeed/rss/rss-canada", languages={"en"}),
        ],
    )
    TheGlobeAndMail = Publisher(
        name="The Globe and Mail",
        domain="https://www.theglobeandmail.com",
        parser=TheGlobeAndMailParser,
        sources=[
            NewsMap(
                "https://www.theglobeandmail.com/arc/outboundfeeds/news-sitemap-index/?outputType=xml", languages={"en"}
            ),
            NewsMap(
                "https://www.theglobeandmail.com/arc/outboundfeeds/sitemap-index/?outputType=xml", languages={"en"}
            ),
        ],
    )

    NationalPost = Publisher(
        name="National Post",
        domain="https://nationalpost.com",
        parser=NationalPostParser,
        sources=[
            NewsMap("https://nationalpost.com/sitemap-news.xml", languages={"en"}),
            Sitemap("https://nationalpost.com/sitemap-old.xml", languages={"en"}),
            RSSFeed("https://nationalpost.com/feed", languages={"en"}),
        ],
    )
