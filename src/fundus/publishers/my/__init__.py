from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.my.malay_mail import MalayMailParser
from fundus.scraping.url import RSSFeed, Sitemap


class MY(metaclass=PublisherGroup):
    MalayMail = Publisher(
        name="Malay Mail",
        domain="https://www.malaymail.com/",
        parser=MalayMailParser,
        sources=[
            Sitemap("https://www.malaymail.com/sitemap.xml", languages={"ms"}),
            RSSFeed("https://www.malaymail.com/feed/rss/", languages={"ms"}),
        ],
    )
