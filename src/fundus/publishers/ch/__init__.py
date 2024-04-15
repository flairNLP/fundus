from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .srf import SRFParser

# noinspection PyPep8Naming


class CH(PublisherEnum):
    SRF = PublisherSpec(
        name="Schweizer Radio und Fernsehen",
        domain="https://www.srf.ch/",
        sources=[
            RSSFeed("https://www.srf.ch/news/bnf/rss/1646"),
            NewsMap("https://www.srf.ch/sitemaps/newsmap/news/index.xml"),
            Sitemap("https://www.srf.ch/new-news-sitemap"),
        ],
        parser=SRFParser,
    )
