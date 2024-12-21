from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.url import RSSFeed, Sitemap

from .people import PeopleParser


class CN(metaclass=PublisherGroup):
    People = Publisher(
        name="People",
        domain="http://www.people.com.cn",
        parser=PeopleParser,
        sources=[
            RSSFeed("http://www.people.com.cn/rss/politics.xml", languages={"zh"}),
            RSSFeed("http://www.people.com.cn/rss/society.xml", languages={"zh"}),
            RSSFeed("http://www.people.com.cn/rss/legal.xml", languages={"zh"}),
            RSSFeed("http://www.people.com.cn/rss/world.xml", languages={"zh"}),
            RSSFeed("http://www.people.com.cn/rss/haixia.xml", languages={"zh"}),
            RSSFeed("http://www.people.com.cn/rss/military.xml", languages={"zh"}),
            RSSFeed("http://www.people.com.cn/rss/ywkx.xml", languages={"zh"}),
            Sitemap("http://www.people.cn/sitemap_index.xml", languages={"zh"}),
        ],
    )
