from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import RSSFeed, Sitemap

from .the_namibian import TheNamibianParser


class NA(PublisherEnum):
    TheNamibian = PublisherSpec(
        name="The Namibian",
        domain="https://www.namibian.com.na/",
        sources=[
            RSSFeed("https://www.namibian.com.na/feed/"),
            Sitemap(
                "https://namibian.com.na/sitemap_index.xml",
                sitemap_filter=inverse(regex_filter("post-sitemap")),
                reverse=True,
            ),
        ],
        parser=TheNamibianParser,
    )
