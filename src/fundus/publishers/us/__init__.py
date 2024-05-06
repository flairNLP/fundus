from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.filter import inverse, lor, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .ap_news import APNewsParser
from .business_insider import BusinessInsiderParser
from .cnbc import CNBCParser
from .fox_news import FoxNewsParser
from .free_beacon import FreeBeaconParser
from .la_times import LATimesParser
from .occupy_democrats import OccupyDemocratsParser
from .reuters import ReutersParser
from .rolling_stone import RollingStoneParser
from .techcrunch import TechCrunchParser
from .the_gateway_pundit import TheGatewayPunditParser
from .the_intercept import TheInterceptParser
from .the_nation_parser import TheNationParser
from .the_new_yorker import TheNewYorkerParser
from .voice_of_america import VOAParser
from .washington_post import WashingtonPostParser
from .washington_times_parser import WashingtonTimesParser
from .wired import WiredParser
from .world_truth import WorldTruthParser


class US(PublisherEnum):
    APNews = PublisherSpec(
        name="Associated Press News",
        domain="https://apnews.com/",
        sources=[
            Sitemap(
                "https://apnews.com/sitemap.xml",
                sitemap_filter=regex_filter("apnews.com/hub/|apnews.com/video/"),
                reverse=True,
            ),
            NewsMap("https://apnews.com/news-sitemap-content.xml"),
        ],
        parser=APNewsParser,
    )

    CNBC = PublisherSpec(
        name="CNBC",
        domain="https://www.cnbc.com/",
        sources=[Sitemap("https://www.cnbc.com/sitemapAll.xml"), NewsMap("https://www.cnbc.com/sitemap_news.xml")],
        parser=CNBCParser,
    )

    TechCrunch = PublisherSpec(
        name="TechCrunch",
        domain="https://techcrunch.com/",
        sources=[
            Sitemap(
                "https://techcrunch.com/sitemap_index.xml",
                sitemap_filter=inverse(regex_filter("post-sitemap")),
                reverse=True,
            ),
            NewsMap("https://techcrunch.com/news-sitemap.xml"),
        ],
        parser=TechCrunchParser,
    )

    TheIntercept = PublisherSpec(
        name="The Intercept",
        domain="https://theintercept.com/",
        sources=[
            RSSFeed("https://theintercept.com/feed/?lang=en"),
            Sitemap(
                "https://theintercept.com/sitemap_index.xml",
                reverse=True,
                sitemap_filter=inverse(regex_filter("post-sitemap")),
            ),
        ],
        parser=TheInterceptParser,
    )

    TheGatewayPundit = PublisherSpec(
        name="The Gateway Pundit",
        domain="https://www.thegatewaypundit.com/",
        sources=[
            Sitemap(
                "https://www.thegatewaypundit.com/sitemap_index.xml",
                sitemap_filter=inverse(regex_filter("post-sitemap")),
                reverse=True,
            ),
            NewsMap("https://www.thegatewaypundit.com/news-sitemap.xml"),
        ],
        parser=TheGatewayPunditParser,
    )

    FoxNews = PublisherSpec(
        name="Fox News",
        domain="https://www.foxnews.com/",
        sources=[
            Sitemap("https://www.foxnews.com/sitemap.xml", sitemap_filter=inverse(regex_filter("type=articles"))),
            NewsMap("https://www.foxnews.com/sitemap.xml?type=news"),
        ],
        parser=FoxNewsParser,
    )

    TheNation = PublisherSpec(
        name="The Nation",
        domain="https://www.thenation.com/",
        sources=[
            Sitemap(
                "https://www.thenation.com/sitemap_index.xml",
                sitemap_filter=inverse(regex_filter("article-sitemap")),
                reverse=True,
            ),
            NewsMap("https://www.thenation.com/news-sitemap.xml"),
        ],
        parser=TheNationParser,
    )

    # WorldTruth = PublisherSpec(
    #     name="World Truth",
    #     domain="https://www.worldtruth.tv/",
    #     sources=[RSSFeed("https://feeds.feedburner.com/ConsciousnessTv")],
    #     parser=WorldTruthParser,
    # )

    FreeBeacon = PublisherSpec(
        name="The Washington Free Beacon",
        domain="https://freebeacon.com/",
        sources=[NewsMap("https://freebeacon.com/post_google_news.xml")],
        parser=FreeBeaconParser,
    )

    WashingtonTimes = PublisherSpec(
        name="The Washington Times",
        domain="https://www.washingtontimes.com/",
        sources=[
            RSSFeed("https://www.washingtontimes.com/rss/headlines/news/politics/"),
            Sitemap("https://www.washingtontimes.com/sitemap-stories.xml"),
            Sitemap("https://www.washingtontimes.com/sitemap-entries.xml"),
        ],
        parser=WashingtonTimesParser,
    )

    WashingtonPost = PublisherSpec(
        name="Washington Post",
        domain="https://www.washingtonpost.com/",
        sources=[
            Sitemap("https://www.washingtonpost.com/sitemaps/sitemap.xml.gz"),
            NewsMap("https://www.washingtonpost.com/sitemaps/news-sitemap.xml.gz"),
            RSSFeed("https://feeds.washingtonpost.com/rss/world"),
            RSSFeed("https://feeds.washingtonpost.com/rss/national"),
        ],
        parser=WashingtonPostParser,
        # Adds a URL-filter to ignore incomplete URLs
        url_filter=regex_filter("washingtonpost.com(\/)?$"),
    )

    TheNewYorker = PublisherSpec(
        name="The New Yorker",
        domain="https://www.newyorker.com/",
        sources=[
            Sitemap("https://www.newyorker.com/sitemap.xml"),
            NewsMap("https://www.newyorker.com/feed/google-news-sitemap-feed/sitemap-google-news"),
        ],
        parser=TheNewYorkerParser,
    )

    Reuters = PublisherSpec(
        name="Reuters",
        domain="https://www.reuters.com/",
        sources=[
            Sitemap("https://www.reuters.com/arc/outboundfeeds/sitemap-index/?outputType=xml"),
            NewsMap("https://www.reuters.com/arc/outboundfeeds/news-sitemap-index/?outputType=xml"),
        ],
        parser=ReutersParser,
    )

    OccupyDemocrats = PublisherSpec(
        name="Occupy Democrats",
        domain="https://occupydemocrats.com/",
        sources=[
            Sitemap(
                url="https://occupydemocrats.com/sitemap.xml", sitemap_filter=inverse(regex_filter(r"post-sitemap"))
            )
        ],
        parser=OccupyDemocratsParser,
    )

    LATimes = PublisherSpec(
        name="Los Angeles Times",
        domain="https://www.latimes.com/",
        sources=[Sitemap("https://www.latimes.com/sitemap.xml"), NewsMap("https://www.latimes.com/news-sitemap.xml")],
        parser=LATimesParser,
    )

    BusinessInsider = PublisherSpec(
        name="Business Insider",
        domain="https://www.businessinsider.com/",
        sources=[
            NewsMap("https://www.businessinsider.com/sitemap/google-news.xml"),
            Sitemap("https://www.businessinsider.com/sitemap/2024-01.xml"),
        ],
        parser=BusinessInsiderParser,
    )

    RollingStone = PublisherSpec(
        name="Rolling Stone",
        domain="https://www.rollingstone.com/",
        sources=[
            NewsMap("https://www.rollingstone.com/news-sitemap.xml"),
            Sitemap(
                "https://www.rollingstone.com/sitemap_index.xml",
                sitemap_filter=inverse(lor(regex_filter("/pmc_list-sitemap"), regex_filter("/post-sitemap"))),
            ),
        ],
        parser=RollingStoneParser,
    )

    VoiceOfAmerica = PublisherSpec(
        name="Voice Of America",
        domain="https://www.voanews.com/",
        sources=[
            NewsMap("https://www.voanews.com/sitemap_415_news.xml.gz"),
            Sitemap(
                "https://www.voanews.com/sitemap.xml", sitemap_filter=inverse(regex_filter(r"sitemap_[\d_]*\.xml\.gz"))
            ),
        ],
        parser=VOAParser,
    )

    Wired = PublisherSpec(
        name="Wired",
        domain="https://www.wired.com",
        sources=[
            RSSFeed("https://www.wired.com/feed/rss"),
            NewsMap("https://www.wired.com/feed/google-latest-news/sitemap-google-news"),
            Sitemap("https://www.wired.com/sitemap.xml"),
            Sitemap("https://www.wired.com/sitemap-archive-1.xml"),
        ],
        parser=WiredParser,
    )
