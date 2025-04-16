from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.url import RSSFeed, Sitemap

from .morgunbladid import MorgunbladidParser

# noinspection PyPep8Naming


class ISL(metaclass=PublisherGroup):
    default_language = "is"

    Morgunbladid = Publisher(
        name="Morgunbladid",
        domain="https://www.mbl.is/",
        parser=MorgunbladidParser,
        sources=[
            Sitemap("https://www.mbl.is/mm/sitemap.xml"),
            RSSFeed("https://www.mbl.is/feeds/fp/"),
            RSSFeed("https://www.mbl.is/feeds/innlent/"),
            RSSFeed("https://www.mbl.is/feeds/erlent/"),
            RSSFeed("https://www.mbl.is/feeds/english/"),
            RSSFeed("https://www.mbl.is/feeds/helst/"),
        ],
    )
