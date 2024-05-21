from fundus.publishers.base_objects import PublisherGroup, Publisher
from fundus.publishers.my.malay_mail import MalayMailParser
from fundus.scraping.url import RSSFeed, Sitemap


class MY(metaclass=PublisherGroup):
    MalayMail = Publisher(
        name="Malay Mail",
        domain="https://www.malaymail.com/",
        sources=[
            Sitemap("https://www.malaymail.com/sitemap.xml"),
            RSSFeed("https://www.malaymail.com/feed/rss/"),
        ],
        parser=MalayMailParser,
    )
