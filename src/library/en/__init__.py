from src.library.collection.base_objects import PublisherEnum, PublisherSpec
from src.library.en.ap_news import APNewsParser


class EN(PublisherEnum):
    APNews = PublisherSpec(
        domain="https://apnews.com/",
        sitemaps=["https://apnews.com/sitemap/google-news-sitemap/google_news_sitemap_1.xml"],
        parser=APNewsParser,
    )
