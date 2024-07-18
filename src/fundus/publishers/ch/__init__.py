from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from ...scraping.filter import inverse, regex_filter
from .nzz import NZZParser
from .srf import SRFParser

# noinspection PyPep8Naming


class CH(metaclass=PublisherGroup):
    SRF = Publisher(
        name="Schweizer Radio und Fernsehen",
        domain="https://www.srf.ch/",
        parser=SRFParser,
        sources=[
            RSSFeed("https://www.srf.ch/news/bnf/rss/1646"),
            NewsMap("https://www.srf.ch/sitemaps/newsmap/news/index.xml"),
            Sitemap("https://www.srf.ch/new-news-sitemap"),
        ],
    )

    NZZ = Publisher(
        name="Neue Zürcher Zeitung (NZZ)",
        domain="https://www.nzz.ch/",
        parser=NZZParser,
        sources=[
            NewsMap("https://www.nzz.ch/sitemap/news0.xml"),
            Sitemap("https://www.nzz.ch/sitemap.xml", sitemap_filter=inverse(regex_filter(r"sitemap/[\d]{4}/[\d]{2}"))),
        ],
    )
