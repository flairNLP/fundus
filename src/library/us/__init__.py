from src.library.collection.base_objects import PublisherEnum, PublisherSpec

from .ap_news import APNewsParser
from .fox_news import FoxNewsParser
from .free_beacon import FreeBeaconParser
from .the_gateway_pundit import TheGatewayPunditParser
from .washington_times_parser import WashingtonTimesParser


class US(PublisherEnum):
    APNews = PublisherSpec(
        domain="https://apnews.com/",
        sitemaps=["https://apnews.com/sitemap/sitemaps/sitemap_index.xml"],
        news_map="https://apnews.com/sitemap/google-news-sitemap/sitemap_index.xml",
        parser=APNewsParser,
    )

    TheGatewayPundit = PublisherSpec(
        domain="https://www.thegatewaypundit.com/",
        sitemaps=["https://www.thegatewaypundit.com/sitemap_index.xml"],
        news_map="https://www.thegatewaypundit.com/news-sitemap.xml",
        parser=TheGatewayPunditParser,
    )

    FoxNews = PublisherSpec(
        domain="https://foxnews.com/",
        sitemaps=[" https://www.foxnews.com/sitemap.xml"],
        news_map="https://www.foxnews.com/sitemap.xml?type=news",
        parser=FoxNewsParser,
    )

    FreeBeacon = PublisherSpec(
        domain="https://freebeacon.com/",
        news_map="https://freebeacon.com/post_google_news.xml",
        parser=FreeBeaconParser,
    )

    WashingtonTimes = PublisherSpec(
        domain="https://www.washingtontimes.com/",
        rss_feeds=["https://www.washingtontimes.com/rss/headlines/news/politics/"],
        sitemaps=[
            "https://www.washingtontimes.com/sitemap-stories.xml",
            "https://www.washingtontimes.com/sitemap-entries.xml",
        ],
        parser=WashingtonTimesParser,
    )
