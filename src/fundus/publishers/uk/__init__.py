from fundus.publishers.base_objects import PublisherEnum, PublisherSpec

from .the_guardian import TheGuardianParser


class UK(PublisherEnum):
    TheGuardian = PublisherSpec(
        domain="https://theguardian.com/",
        news_map="http://www.theguardian.com/sitemaps/news.xml",
        parser=TheGuardianParser,
    )
