from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.url import NewsMap, Sitemap

from .haberturk import HaberturkParser


class TR(PublisherEnum):
    Haberturk = PublisherSpec(
        name="Haberturk",
        domain="https://www.haberturk.com/",
        sources=[
            Sitemap("https://www.haberturk.com/sitemap.xml"),
            NewsMap("https://www.haberturk.com/sitemap_google_news.xml"),
        ],
        parser=HaberturkParser,
    )
