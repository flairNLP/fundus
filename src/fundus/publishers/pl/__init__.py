from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.pl.rzeczpospolita import RzeczpospolitaParser
from fundus.scraping.url import NewsMap, Sitemap


class PL(metaclass=PublisherGroup):
    default_language = "pl"

    Rzeczpospolita = Publisher(
        name="Rzeczpospolita",
        domain="https://www.rp.pl/",
        parser=RzeczpospolitaParser,
        sources=[
            Sitemap(
                "https://www.rp.pl/sitemaps/sitemap.xml",
            ),
            NewsMap("https://www.rp.pl/sitemaps/news-sitemap.xml"),
        ],
    )
