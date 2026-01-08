from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import Sitemap, NewsMap, RSSFeed

from .aftonbladet import AftonbladetParser

class SE(metaclass=PublisherGroup):
    default_language = "se"

    Aftonbladet = Publisher(
        name="Aftonbladet",
        domain="https://www.aftonbladet.se/",
        parser=AftonbladetParser,
        sources=[
            Sitemap(
                "https://www.aftonbladet.se/sitemap.xml",
                sitemap_filter=inverse(regex_filter("articles.xml")),
                reverse=True,
            ),
            NewsMap("https://www.aftonbladet.se/sitemaps/files/articles-48hrs.xml"),
            RSSFeed("https://rss.aftonbladet.se/rss2/small/pages/sections/senastenytt/")
        ],
    )
