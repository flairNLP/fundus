from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import Sitemap

from .aftonbladet import AftonbladetParser


class SE(metaclass=PublisherGroup):
    default_language = "se"
    
    Aftonbladet = Publisher(
        name="Aftonbladet",
        domain="https://www.aftonbladet.se/",
        parser=AftonbladetParser,
        sources=[
            Sitemap("https://www.aftonbladet.se/sitemap.xml", 
                    sitemap_filter=inverse(regex_filter("articles.xml")), 
                    reverse=True,
            ),
        ],
    )
