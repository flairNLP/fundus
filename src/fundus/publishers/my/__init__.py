from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.publishers.my.malay_mail import MalayMailParser
from fundus.scraping.url import RSSFeed, Sitemap


class MY(PublisherEnum):
    MalayMail = PublisherSpec(
        name="Malay Mail",
        domain="https://www.malaymail.com/",
        sources=[
            Sitemap("https://www.malaymail.com/sitemap.xml"),
            RSSFeed("https://www.malaymail.com/feed/rss/"),
        ],
        parser=MalayMailParser,
    )
