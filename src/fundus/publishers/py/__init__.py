from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.url import Sitemap

from ...scraping.filter import inverse, regex_filter
from .wochenblatt import WochenblattParser


class PY(metaclass=PublisherGroup):
    default_language = "es"

    Wochenblatt = Publisher(
        name="Wochenblatt",
        domain="https://wochenblatt.cc/",
        parser=WochenblattParser,
        sources=[
            Sitemap(
                "https://wochenblatt.cc/sitemap_index.xml",
                sitemap_filter=inverse(regex_filter("post-")),
                reverse=True,
                languages={"de"},
            ),
        ],
    )
