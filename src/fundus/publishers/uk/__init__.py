from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.html import NewsMap, Sitemap

from .the_guardian import TheGuardianParser
from .the_independent import TheIndependentParser


class UK(PublisherEnum):
    TheGuardian = PublisherSpec(
        name="The Guardian",
        domain="https://www.theguardian.com/",
        sources=[NewsMap("https://www.theguardian.com/sitemaps/news.xml")],
        parser=TheGuardianParser,
    )

    TheIndependent = PublisherSpec(
        name="The Independent",
        domain="https://www.independent.co.uk/",
        sources=[Sitemap("https://www.independent.co.uk/sitemap.xml"),
                 NewsMap("https://www.independent.co.uk/sitemaps/googlenews")],
        parser=TheIndependentParser,
    )

