from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import regex_filter
from fundus.scraping.url import RSSFeed, Sitemap

from .expressen import ExpressenParser


class SE(metaclass=PublisherGroup):
    default_language = "sv"

    Expressen = Publisher(
        name="Expressen",
        domain="https://www.expressen.se/",
        parser=ExpressenParser,
        sources=[
            RSSFeed("https://feeds.expressen.se/nyheter/"),
            RSSFeed("https://feeds.expressen.se/gt"),
            RSSFeed("https://feeds.expressen.se/kvp/"),
            RSSFeed("https://feeds.expressen.se/sport/"),
            RSSFeed("https://feeds.expressen.se/fotboll/"),
            RSSFeed("https://feeds.expressen.se/hockey/"),
            RSSFeed("https://feeds.expressen.se/noje/"),
            RSSFeed("https://feeds.expressen.se/debatt/"),
            RSSFeed("https://feeds.expressen.se/ledare/"),
            RSSFeed("https://feeds.expressen.se/kultur/"),
            RSSFeed("https://feeds.expressen.se/dinapengar/"),
            RSSFeed("https://feeds.expressen.se/halsoliv/"),
            RSSFeed("https://feeds.expressen.se/levabo/"),
            RSSFeed("https://feeds.expressen.se/motor/"),
            RSSFeed("https://feeds.expressen.se/allt-om-resor/"),
            Sitemap("https://www.expressen.se/sitemap.xml", reverse=True),
        ],
        url_filter=regex_filter(r"/tv/|expressen-direkt"),
    )
