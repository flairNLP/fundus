from fundus.publishers.base_objects import PublisherEnum, PublisherSpec

from .ap_news import APNewsParser
from .cnbc import CNBCParser
from .fox_news import FoxNewsParser
from .free_beacon import FreeBeaconParser
from .reuters import ReutersParser
from .the_gateway_pundit import TheGatewayPunditParser
from .the_intercept import TheInterceptParser
from .the_nation_parser import TheNationParser
from .the_new_yorker import TheNewYorkerParser
from .washington_times_parser import WashingtonTimesParser
from .world_truth import WorldTruthParser


class US(PublisherEnum):
    APNews = PublisherSpec(
        name="Associated Press News",
        domain="https://www.apnews.com/",
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
        domain="https://www.theintercept.com/",
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
        domain="https://www.foxnews.com/",
        sitemaps=[" https://www.foxnews.com/sitemap.xml"],
        news_map="https://www.foxnews.com/sitemap.xml?type=news",
        parser=FoxNewsParser,
    )

    TheNation = PublisherSpec(
        name="The Nation",
        domain="https://www.thenation.com/",
        sitemaps=["https://www.thenation.com/sitemap_index.xml"],
        news_map="https://www.thenation.com/news-sitemap.xml",
        parser=TheNationParser,
    )

    WorldTruth = PublisherSpec(
        name="World Truth",
        domain="https://www.worldtruth.tv/",
        rss_feeds=["https://feeds.feedburner.com/ConsciousnessTv"],
        parser=WorldTruthParser,
    )

    FreeBeacon = PublisherSpec(
        name="The Washington Free Beacon",
        domain="https://www.freebeacon.com/",
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

    TheNewYorker = PublisherSpec(
        name="The New Yorker",
        domain="https://www.newyorker.com/",
        sitemaps=["https://www.newyorker.com/sitemap.xml"],
        news_map="https://www.newyorker.com/feed/google-news-sitemap-feed/sitemap-google-news",
        parser=TheNewYorkerParser,
    )

    Reuters = PublisherSpec(
        name="Reuters",
        domain="https://www.reuters.com/",
        sitemaps=["https://www.reuters.com/arc/outboundfeeds/sitemap-index/?outputType=xml"],
        news_map="https://www.reuters.com/arc/outboundfeeds/news-sitemap-index/?outputType=xml",
        parser=ReutersParser,
    )
