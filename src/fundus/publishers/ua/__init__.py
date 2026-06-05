from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, Sitemap

from .pravda import PravdaParser


class UA(metaclass=PublisherGroup):
    default_language = "uk"

    Pravda = Publisher(
        name="Ukrainska Pravda",
        domain="https://www.pravda.com.ua",
        parser=PravdaParser,
        sources=[
            Sitemap("https://www.pravda.com.ua/sitemap/sitemap-archive.xml", languages={"uk", "en", "ru"}),
            NewsMap("https://www.pravda.com.ua/sitemap/sitemap-news.xml", languages={"uk", "en", "ru"}),
        ],
        url_filter=inverse(regex_filter("[^e]pravda.com.ua.")),
    )
