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
        name="Associated Press News",
        domain="https://apnews.com/",
        sitemaps=["https://apnews.com/sitemap/sitemaps/sitemap_index.xml"],
        news_map="https://apnews.com/sitemap/google-news-sitemap/sitemap_index.xml",
        parser=APNewsParser,
    )

    CNBC = PublisherSpec(
        name="CNBC",
        domain="https://www.cnbc.com/",
        sitemaps=["https://www.cnbc.com/sitemapAll.xml"],
        news_map="https://www.cnbc.com/sitemap_news.xml",
        parser=CNBCParser,
    )

    TheIntercept = PublisherSpec(
        name="The Intercept",
        domain="https://theintercept.com/",
        sitemaps=["https://theintercept.com/theintercept/sitemap/master/index/"],
        parser=TheInterceptParser,
    )

    TheGatewayPundit = PublisherSpec(
        name="The Gateway Pundit",
        domain="https://www.thegatewaypundit.com/",
        sitemaps=["https://www.thegatewaypundit.com/sitemap_index.xml"],
        news_map="https://www.thegatewaypundit.com/news-sitemap.xml",
        parser=TheGatewayPunditParser,
    )

    FoxNews = PublisherSpec(
        name="Fox News",
        domain="https://foxnews.com/",
        sitemaps=[" https://www.foxnews.com/sitemap.xml"],
        news_map="https://www.foxnews.com/sitemap.xml?type=news",
        parser=FoxNewsParser,
    )

    WorldTruth = PublisherSpec(
        name="World Truth",
        domain="https://worldtruth.tv/",
        rss_feeds=["https://feeds.feedburner.com/ConsciousnessTv"],
        parser=WorldTruthParser,
    )

    FreeBeacon = PublisherSpec(
        name="The Washington Free Beacon",
        domain="https://freebeacon.com/",
        news_map="https://freebeacon.com/post_google_news.xml",
        parser=FreeBeaconParser,
    )

    WashingtonTimes = PublisherSpec(
        name="The Washington Times",
        domain="https://www.washingtontimes.com/",
        rss_feeds=["https://www.washingtontimes.com/rss/headlines/news/politics/"],
        sitemaps=[
            "https://www.washingtontimes.com/sitemap-stories.xml",
            "https://www.washingtontimes.com/sitemap-entries.xml",
        ],
        parser=WashingtonTimesParser,
    )
