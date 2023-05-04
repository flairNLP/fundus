from fundus.publishers.base_objects import PublisherEnum, PublisherSpec

from .ap_news import APNewsParser
from .cnbc import CNBCParser
from .fox_news import FoxNewsParser
from .free_beacon import FreeBeaconParser
from .the_gateway_pundit import TheGatewayPunditParser
from .the_intercept import TheInterceptParser
from .washington_times_parser import WashingtonTimesParser
from .world_truth import WorldTruthParser


class US(PublisherEnum):
    APNews = PublisherSpec(
        domain="https://apnews.com/",
        sitemaps=["https://apnews.com/sitemap/sitemaps/sitemap_index.xml"],
        news_map="https://apnews.com/sitemap/google-news-sitemap/sitemap_index.xml",
        parser=APNewsParser,
        article_classification_func_generator=lambda: lambda x, y: True,
    )

    CNBC = PublisherSpec(
        domain="https://www.cnbc.com/",
        sitemaps=["https://www.cnbc.com/sitemapAll.xml"],
        news_map="https://www.cnbc.com/sitemap_news.xml",
        parser=CNBCParser,
        article_classification_func_generator=lambda: lambda x, y: True,
    )

    TheIntercept = PublisherSpec(
        domain="https://theintercept.com/",
        sitemaps=["https://theintercept.com/theintercept/sitemap/master/index/"],
        parser=TheInterceptParser,
        article_classification_func_generator=lambda: lambda x, y: True,
    )

    TheGatewayPundit = PublisherSpec(
        domain="https://www.thegatewaypundit.com/",
        sitemaps=["https://www.thegatewaypundit.com/sitemap_index.xml"],
        news_map="https://www.thegatewaypundit.com/news-sitemap.xml",
        parser=TheGatewayPunditParser,
        article_classification_func_generator=lambda: lambda x, y: True,
    )

    FoxNews = PublisherSpec(
        domain="https://foxnews.com/",
        sitemaps=[" https://www.foxnews.com/sitemap.xml"],
        news_map="https://www.foxnews.com/sitemap.xml?type=news",
        parser=FoxNewsParser,
        article_classification_func_generator=lambda: lambda x, y: True,
    )

    WorldTruth = PublisherSpec(
        domain="https://worldtruth.tv/",
        rss_feeds=["https://feeds.feedburner.com/ConsciousnessTv"],
        parser=WorldTruthParser,
        article_classification_func_generator=lambda: lambda x, y: True,
    )

    FreeBeacon = PublisherSpec(
        domain="https://freebeacon.com/",
        news_map="https://freebeacon.com/post_google_news.xml",
        parser=FreeBeaconParser,
        article_classification_func_generator=lambda: lambda x, y: True,
    )

    WashingtonTimes = PublisherSpec(
        domain="https://www.washingtontimes.com/",
        rss_feeds=["https://www.washingtontimes.com/rss/headlines/news/politics/"],
        sitemaps=[
            "https://www.washingtontimes.com/sitemap-stories.xml",
            "https://www.washingtontimes.com/sitemap-entries.xml",
        ],
        parser=WashingtonTimesParser,
        article_classification_func_generator=lambda: lambda x, y: True,
    )
