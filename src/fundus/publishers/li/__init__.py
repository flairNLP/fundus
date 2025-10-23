from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.url import NewsMap, Sitemap

from .landesspiegel import LandesspiegelParser


class LI(metaclass=PublisherGroup):
    default_language = "de"

    Landesspiegel = Publisher(
        name="Landesspiegel",
        domain="https://www.landesspiegel.li",
        parser=LandesspiegelParser,
        sources=[
            NewsMap("https://landesspiegel.li/sitemap-news.xml"),
            Sitemap("https://landesspiegel.li/sitemap-posttype-post.xml"),
        ],
    )
