from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.ls.lesotho_times import LesothoTimesParser
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import Sitemap


class LS(metaclass=PublisherGroup):
    default_language = "en"

    LesothoTimes = Publisher(
        name="Lesotho Times",
        domain="https://lestimes.com/",
        parser=LesothoTimesParser,
        sources=[
            Sitemap(
                "https://lestimes.com/sitemap_index.xml",
                sitemap_filter=inverse(regex_filter("post-sitemap")),
                reverse=True,
            ),
        ],
    )
