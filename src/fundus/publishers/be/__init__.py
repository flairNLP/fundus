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
            RSSFeed("https://www.nieuwsblad.be/rss/section/55178e67-15a8-4ddd-a3d8-bfe5708f8932"),
            RSSFeed("https://www.nieuwsblad.be/rss/section/7f1bc231-66e7-49f0-a126-b7346eb3e2fa"),
            RSSFeed("https://www.nieuwsblad.be/rss/section/3dfcee99-2971-4c4c-a603-8c41ae86398b"),
            RSSFeed("https://www.nieuwsblad.be/rss/section/c0c3b215-10be-4f82-86d6-8b8584a5639d"),
        ],
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
