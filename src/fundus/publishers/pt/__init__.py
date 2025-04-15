from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, lor, regex_filter
from fundus.scraping.url import Sitemap

from .the_portugal_news import ThePortugalNewsParser


class PT(metaclass=PublisherGroup):
    default_language = "pt"

    ThePortugalNews = Publisher(
        name="The Portugal News",
        domain="https://www.theportugalnews.com/",
        parser=ThePortugalNewsParser,
        # There are more languages un the sitemap that could be added in the future
        sources=[
            Sitemap(
                "https://www.theportugalnews.com/sitemap.xml",
                sitemap_filter=lor(regex_filter("category-pages"), inverse(regex_filter("/en/"))),
                languages={"en"},
            ),
        ],
    )
