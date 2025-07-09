from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import Sitemap

from .israel_nachrichten import IsraelNachrichtenParser


class IL(metaclass=PublisherGroup):
    default_language = "he"

    IsraelNachrichten = Publisher(
        name="Israel Nachrichten",
        domain="https://www.israel-nachrichten.org/",
        parser=IsraelNachrichtenParser,
        sources=[
            Sitemap(
                "https://www.israel-nachrichten.org/wp-sitemap.xml",
                reverse=True,
                sitemap_filter=inverse(regex_filter("posts-post")),
                languages={"de"},
            )
        ],
    )
