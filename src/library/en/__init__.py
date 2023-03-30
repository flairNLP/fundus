from src.library.collection.base_objects import PublisherEnum, PublisherSpec
from src.library.en.ap_news import APNewsParser
from src.library.en.cnbc import CNBCParser


class US(PublisherEnum):
    APNews = PublisherSpec(
        domain="https://apnews.com/",
        sitemaps=["https://apnews.com/sitemap/sitemaps/sitemap_index.xml"],
        news_map="https://apnews.com/sitemap/google-news-sitemap/sitemap_index.xml",
        parser=APNewsParser,
    )

    CNBC = PublisherSpec(
        domain="https://www.cnbc.com/",
        sitemaps=["https://www.cnbc.com/sitemap_news.xml"],
        parser=CNBCParser,
    )
