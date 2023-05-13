from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.source_url import NewsMap, RSSFeed, Sitemap

from .ap_news import APNewsParser
from .cnbc import CNBCParser
from .fox_news import FoxNewsParser
from .free_beacon import FreeBeaconParser
from .the_gateway_pundit import TheGatewayPunditParser
from .the_intercept import TheInterceptParser
from .the_nation_parser import TheNationParser
from .washington_times_parser import WashingtonTimesParser
from .world_truth import WorldTruthParser


class US(PublisherEnum):
    APNews = PublisherSpec(
        domain="https://apnews.com/",
        sources=[
            Sitemap("https://apnews.com/sitemap/sitemaps/sitemap_index.xml"),
            NewsMap("https://apnews.com/sitemap/google-news-sitemap/sitemap_index.xml"),
        ],
        parser=APNewsParser,
    )

    CNBC = PublisherSpec(
        domain="https://www.cnbc.com/",
        sources=[Sitemap("https://www.cnbc.com/sitemapAll.xml"), NewsMap("https://www.cnbc.com/sitemap_news.xml")],
        parser=CNBCParser,
    )

    TheIntercept = PublisherSpec(
        domain="https://theintercept.com/",
        sources=[Sitemap("https://theintercept.com/theintercept/sitemap/master/index/")],
        parser=TheInterceptParser,
    )

    TheGatewayPundit = PublisherSpec(
        domain="https://www.thegatewaypundit.com/",
        sources=[
            Sitemap("https://www.thegatewaypundit.com/sitemap_index.xml"),
            NewsMap("https://www.thegatewaypundit.com/news-sitemap.xml"),
        ],
        parser=TheGatewayPunditParser,
    )

    FoxNews = PublisherSpec(
        domain="https://foxnews.com/",
        sources=[
            Sitemap(" https://www.foxnews.com/sitemap.xml"),
            NewsMap("https://www.foxnews.com/sitemap.xml?type=news"),
        ],
        parser=FoxNewsParser,
    )

    TheNation = PublisherSpec(
        domain="https://www.thenation.com/",
        sources=[
            Sitemap("https://www.thenation.com/sitemap_index.xml"),
            NewsMap("https://www.thenation.com/news-sitemap.xml"),
        ],
        parser=TheNationParser,
    )

    WorldTruth = PublisherSpec(
        domain="https://worldtruth.tv/",
        sources=[RSSFeed("https://feeds.feedburner.com/ConsciousnessTv")],
        parser=WorldTruthParser,
    )

    FreeBeacon = PublisherSpec(
        domain="https://freebeacon.com/",
        sources=[NewsMap("https://freebeacon.com/post_google_news.xml")],
        parser=FreeBeaconParser,
    )

    WashingtonTimes = PublisherSpec(
        domain="https://www.washingtontimes.com/",
        sources=[
            RSSFeed("https://www.washingtontimes.com/rss/headlines/news/politics/"),
            Sitemap("https://www.washingtontimes.com/sitemap-stories.xml"),
            Sitemap("https://www.washingtontimes.com/sitemap-entries.xml"),
        ],
        parser=WashingtonTimesParser,
    )
