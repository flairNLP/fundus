from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.url import RSSFeed, Sitemap

from .adevarul import AdevarulParser


class RO(PublisherEnum):
    Adevarul = PublisherSpec(
        name="Adevarul",
        domain="https://adevarul.ro/",
        sources=[RSSFeed("https://adevarul.ro/rss/index"), Sitemap("https://adevarul.ro/_r/google_news_sitemap.xml")],
        parser=AdevarulParser,
    )
