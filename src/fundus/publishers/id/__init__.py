from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.id.media_indonesia import MediaIndonesiaParser
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import Sitemap


class ID(metaclass=PublisherGroup):
    default_language = "id"

    MediaIndonesia = Publisher(
        name="Media Indonesia",
        domain="https://www.mediaindonesia.com/",
        parser=MediaIndonesiaParser,
        sources=[Sitemap("https://mediaindonesia.com/sitemap.xml")],
    )
