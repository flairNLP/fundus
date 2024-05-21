from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import RSSFeed, Sitemap

from .the_namibian import TheNamibianParser


class NA(metaclass=PublisherGroup):
    TheNamibian = Publisher(
        name="The Namibian",
        domain="https://www.namibian.com.na/",
        parser=TheNamibianParser,
        sources=[
            RSSFeed("https://www.namibian.com.na/feed/"),
            Sitemap(
                "https://namibian.com.na/sitemap_index.xml",
                sitemap_filter=inverse(regex_filter("post-sitemap")),
                reverse=True,
            ),
        ],
    )
