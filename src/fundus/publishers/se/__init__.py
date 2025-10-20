from fundus.publishers.base_objects import PublisherGroup,Publisher
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .expressen import ExpressenParser

class SE(metaclass=PublisherGroup):
    default_language = "sv"

    Expressen = Publisher(
        name="Expressen",
        domain="https://www.expressen.se/",
        parser=ExpressenParser,
        sources=[
            RSSFeed("https://feeds.expressen.se/nyheter/"),
            RSSFeed("https://feeds.expressen.se/sport/"),
            RSSFeed("https://feeds.expressen.se/noje/"),
            Sitemap("https://www.expressen.se/sitemap.xml"),
        ],
    )