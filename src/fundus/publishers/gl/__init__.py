from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.url import Sitemap

from .sermitsiaq import SermitsiaqParser


class GL(metaclass=PublisherGroup):
    default_language = "kl"

    Sermitsiaq = Publisher(
        name="Sermitsiaq",
        domain="https://www.sermitsiaq.ag/",
        parser=SermitsiaqParser,
        sources=[Sitemap("https://www.sermitsiaq.ag/sitemap.xml")],
    )
