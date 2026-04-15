from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.be.nieuwsblad import NieuwsbladParser
from fundus.publishers.be.politico_eu import PoliticoEuParser
from fundus.scraping.filter import regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap


class BE(metaclass=PublisherGroup):
    default_language = "nl"

    Nieuwsblad = Publisher(
        name="Nieuwsblad",
        domain="https://www.nieuwsblad.be/",
        parser=NieuwsbladParser,
        sources=[
            RSSFeed("https://www.nieuwsblad.be/rss/"),
            NewsMap("https://www.nieuwsblad.be/sitemap-news.xml"),
            Sitemap("https://www.nieuwsblad.be/sitemap.xml"),
        ],
        deprecated=True,
    )

    PoliticoEu = Publisher(
        name="Politico EU",
        domain="https://www.politico.eu/",
        parser=PoliticoEuParser,
        sources=[
            RSSFeed("https://www.politico.eu/feed/", languages={"en"}),
            Sitemap("https://www.politico.eu/sitemap.xml", languages={"en"}),
            NewsMap("https://www.politico.eu/news-sitemap.xml", languages={"en"}),
        ],
        url_filter=regex_filter("/podcast/"),
    )
