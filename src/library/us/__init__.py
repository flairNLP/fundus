from src.library.collection.base_objects import PublisherEnum, PublisherSpec

from .ap_news import APNewsParser
from .cnbc import CNBCParser
from .fox_news import FoxNewsParser


class US(PublisherEnum):
    APNews = PublisherSpec(
        domain="https://apnews.com/",
        sitemaps=["https://apnews.com/sitemap/sitemaps/sitemap_index.xml"],
        news_map="https://apnews.com/sitemap/google-news-sitemap/sitemap_index.xml",
        parser=APNewsParser,
    )

    CNBC = PublisherSpec(
        domain="https://www.cnbc.com/",
        sitemaps=["https://www.cnbc.com/sitemapAll.xml"],
        news_map="https://www.cnbc.com/sitemap_news.xml",
        parser=CNBCParser,
    )

    FoxNews = PublisherSpec(
        domain="https://foxnews.com/",
        sitemaps=[" https://www.foxnews.com/sitemap.xml"],
        news_map="https://www.foxnews.com/sitemap.xml?type=news",
        parser=FoxNewsParser,
    )
