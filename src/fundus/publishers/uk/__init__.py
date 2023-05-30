from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.source import NewsMap

from .the_guardian import TheGuardianParser


class UK(PublisherEnum):
    TheGuardian = PublisherSpec(
        domain="https://www.theguardian.com/",
        sources=[NewsMap("https://www.theguardian.com/sitemaps/news.xml")],
        parser=TheGuardianParser,
    )
