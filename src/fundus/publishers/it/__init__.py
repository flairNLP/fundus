from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.it.la_repubblica import LaRepubblicaParser
from fundus.scraping.url import RSSFeed, Sitemap


class IT(metaclass=PublisherGroup):
    LaRepubblica = Publisher(
        name="La Repubblica",
        domain="https://www.repubblica.it",
        parser=LaRepubblicaParser,
        sources=[
            RSSFeed("https://www.repubblica.it/rss/homepage/rss2.0.xml"),
            Sitemap("https://www.repubblica.it/sitemap.xml", reverse=True, recursive=False),
        ],
    )
