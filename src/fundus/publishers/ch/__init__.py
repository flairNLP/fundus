from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from ...scraping.filter import inverse, regex_filter
from .nzz import NZZParser
from .srf import SRFParser
from .ta import TAParser
from .zwanzig_minuten import ZwanzigMinutenParser

# noinspection PyPep8Naming


class CH(metaclass=PublisherGroup):
    default_language = "de"

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
            Sitemap(
                "https://www.nzz.ch/sitemap.xml",
                sitemap_filter=inverse(regex_filter(r"sitemap/[\d]{4}/[\d]{2}")),
            ),
        ],
    )

    TagesAnzeiger = Publisher(
        name="Tages-Anzeiger",
        domain="https://www.tagesanzeiger.ch/",
        parser=TAParser,
        sources=[
            NewsMap("https://www.tagesanzeiger.ch/sitemaps/news.xml"),
            Sitemap(
                "https://www.tagesanzeiger.ch/sitemaps/sitemapindex.xml",
                reverse=True,
                sitemap_filter=regex_filter("news|category"),
            ),
        ],
    )
    ZwanzigMinuten = Publisher(
        name="Zwanzig Minuten",
        domain="https://www.20min.ch/",
        parser=ZwanzigMinutenParser,
        sources=[
            NewsMap("https://www.20min.ch/sitemaps/de/news.xml"),
            Sitemap("https://www.20min.ch/sitemaps/de/articles.xml"),
            NewsMap("https://www.20min.ch/sitemaps/fr/news.xml"),
            Sitemap("https://www.20min.ch/sitemaps/fr/articles.xml"),
        ],
    )
