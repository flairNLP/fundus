from fundus.publishers.base_objects import NewsMap, PublisherEnum, PublisherSpec

from .the_guardian import TheGuardianParser


class UK(PublisherEnum):
    TheGuardian = PublisherSpec(
        domain="https://www.theguardian.com/",
        sources=[NewsMap("https://www.theguardian.com/sitemaps/news.xml")],
        parser=TheGuardianParser,
    )
