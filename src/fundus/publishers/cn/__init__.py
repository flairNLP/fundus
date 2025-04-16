from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.url import RSSFeed, Sitemap

from .people import PeopleParser


class CN(metaclass=PublisherGroup):
    default_language = "zh"

    People = Publisher(
        name="People",
        domain="http://www.people.com.cn",
        parser=PeopleParser,
        sources=[
            RSSFeed("http://www.people.com.cn/rss/politics.xml"),
            RSSFeed("http://www.people.com.cn/rss/society.xml"),
            RSSFeed("http://www.people.com.cn/rss/legal.xml"),
            RSSFeed("http://www.people.com.cn/rss/world.xml"),
            RSSFeed("http://www.people.com.cn/rss/haixia.xml"),
            RSSFeed("http://www.people.com.cn/rss/military.xml"),
            RSSFeed("http://www.people.com.cn/rss/ywkx.xml"),
            Sitemap("http://www.people.cn/sitemap_index.xml"),
        ],
    )
