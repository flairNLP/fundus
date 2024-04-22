from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .people import PeopleParser


class CN(PublisherEnum):
    People = PublisherSpec(
        name='People',
        domain="https://www.people.com.cn",
        sources=[Sitemap("https://www.people.cn/sitemap_index.xml"),
                 NewsMap("https://politics.people.com.cn/news_sitemap.xml")],
        parser=PeopleParser,
    )
