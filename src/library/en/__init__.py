from src.library.collection.base_objects import PublisherEnum, PublisherSpec
from src.library.en.fox_news import FoxNewsParser

class EN(PublisherEnum):
    FoxNews = PublisherSpec(
        domain="https://foxnews.com/",
        sitemaps=[" https://www.foxnews.com/sitemap.xml"],
        parser=FoxNewsParser,
    )

