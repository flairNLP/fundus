from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import Sitemap

from .jyllands_posten import JyllandsPostenParser


class DK(metaclass=PublisherGroup):
    default_language = "da"

    JyllandsPosten = Publisher(
        name="Jyllands Posten",
        domain="https://jyllands-posten.dk/",
        parser=JyllandsPostenParser,
        sources=[
            Sitemap(
                "https://jyllands-posten.dk/sitemapindex.xml",
                reverse=True,
            ),
        ],
        url_filter=inverse(regex_filter(r"/ECE")),
    )
