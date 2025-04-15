from fundus.publishers.base_objects import Publisher, PublisherGroup
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
from .the_nation import TheNationParser
from .the_new_yorker import TheNewYorkerParser
from .voice_of_america import VOAParser
from .washington_post import WashingtonPostParser
from .washington_times import WashingtonTimesParser
from .wired import WiredParser
from .world_truth import WorldTruthParser


class US(metaclass=PublisherGroup):
    default_language = "en"

    APNews = Publisher(
        name="Associated Press News",
        domain="https://apnews.com/",
        parser=APNewsParser,
        sources=[
            Sitemap(
                "https://apnews.com/sitemap.xml",
                sitemap_filter=regex_filter("apnews.com/hub/|apnews.com/video/"),
                reverse=True,
                languages={"en", "es"},
            ),
            NewsMap("https://apnews.com/news-sitemap-content.xml", languages={"en", "es"}),
        ],
    )

    CNBC = Publisher(
        name="CNBC",
        domain="https://www.cnbc.com/",
        parser=CNBCParser,
        sources=[
            Sitemap("https://www.cnbc.com/sitemapAll.xml"),
            NewsMap("https://www.cnbc.com/sitemap_news.xml"),
        ],
    )

    TechCrunch = Publisher(
        name="TechCrunch",
        domain="https://techcrunch.com/",
        parser=TechCrunchParser,
        sources=[
            Sitemap(
                "https://techcrunch.com/sitemap_index.xml",
                sitemap_filter=inverse(regex_filter("post-sitemap")),
                reverse=True,
            ),
            NewsMap("https://techcrunch.com/news-sitemap.xml"),
        ],
    )

    TheIntercept = Publisher(
        name="The Intercept",
        domain="https://theintercept.com/",
        parser=TheInterceptParser,
        sources=[
            RSSFeed("https://theintercept.com/feed/?lang=en"),
            Sitemap(
                "https://theintercept.com/sitemap_index.xml",
                reverse=True,
                sitemap_filter=inverse(regex_filter("post-sitemap")),
            ),
        ],
    )

    TheGatewayPundit = Publisher(
        name="The Gateway Pundit",
        domain="https://www.thegatewaypundit.com/",
        parser=TheGatewayPunditParser,
        sources=[
            Sitemap(
                "https://www.thegatewaypundit.com/sitemap_index.xml",
                sitemap_filter=inverse(regex_filter("post-sitemap")),
                reverse=True,
            ),
            NewsMap("https://www.thegatewaypundit.com/news-sitemap.xml"),
        ],
    )

    FoxNews = Publisher(
        name="Fox News",
        domain="https://www.foxnews.com/",
        parser=FoxNewsParser,
        url_filter=regex_filter(r"\/video\/"),
        sources=[
            Sitemap(
                "https://www.foxnews.com/sitemap.xml",
                sitemap_filter=inverse(regex_filter("type=articles")),
            ),
            NewsMap("https://www.foxnews.com/sitemap.xml?type=news"),
            RSSFeed("https://moxie.foxnews.com/google-publisher/latest.xml"),
            RSSFeed("https://moxie.foxnews.com/google-publisher/world.xml"),
            RSSFeed("https://moxie.foxnews.com/google-publisher/politics.xml"),
            RSSFeed("https://moxie.foxnews.com/google-publisher/us.xml"),
            RSSFeed("https://moxie.foxnews.com/google-publisher/world.xml"),
            RSSFeed("https://moxie.foxnews.com/google-publisher/travel.xml"),
            RSSFeed("https://moxie.foxnews.com/google-publisher/opinion.xml"),
            RSSFeed("https://moxie.foxnews.com/google-publisher/tech.xml"),
            RSSFeed("https://moxie.foxnews.com/google-publisher/science.xml"),
            RSSFeed("https://moxie.foxnews.com/google-publisher/health.xml"),
        ],
    )

    TheNation = Publisher(
        name="The Nation",
        domain="https://www.thenation.com/",
        parser=TheNationParser,
        sources=[
            Sitemap(
                "https://www.thenation.com/sitemap_index.xml",
                sitemap_filter=inverse(regex_filter("article-sitemap")),
                reverse=True,
            ),
            NewsMap("https://www.thenation.com/news-sitemap.xml"),
        ],
    )

    # WorldTruth = Publisher(
    #     name="World Truth",
    #     domain="https://www.worldtruth.tv/",
    #     sources=[RSSFeed("https://feeds.feedburner.com/ConsciousnessTv")],
    #     parser=WorldTruthParser,
    # )

    FreeBeacon = Publisher(
        name="The Washington Free Beacon",
        domain="https://freebeacon.com/",
        sources=[
            Sitemap(
                "https://freebeacon.com/wp-sitemap.xml",
                sitemap_filter=inverse(regex_filter("post-sitemap")),
                reverse=True,
            ),
            Sitemap(
                "https://freebeacon.com/wp-sitemap.xml",
                sitemap_filter=inverse(regex_filter("blog-sitemap")),
                reverse=True,
            ),
        ],
        parser=FreeBeaconParser,
    )

    WashingtonTimes = Publisher(
        name="The Washington Times",
        domain="https://www.washingtontimes.com/",
        parser=WashingtonTimesParser,
        sources=[
            RSSFeed("https://www.washingtontimes.com/rss/headlines/news/politics/"),
            Sitemap("https://www.washingtontimes.com/sitemap-stories.xml"),
            Sitemap("https://www.washingtontimes.com/sitemap-entries.xml"),
        ],
        deprecated=True,
    )

    WashingtonPost = Publisher(
        name="Washington Post",
        domain="https://www.washingtonpost.com/",
        parser=WashingtonPostParser,
        sources=[
            Sitemap("https://www.washingtonpost.com/sitemaps/sitemap.xml.gz"),
            NewsMap("https://www.washingtonpost.com/sitemaps/news-sitemap.xml.gz"),
            RSSFeed("https://feeds.washingtonpost.com/rss/world"),
            RSSFeed("https://feeds.washingtonpost.com/rss/national"),
        ],
        # Adds a URL-filter to ignore incomplete URLs
        url_filter=regex_filter(r"washingtonpost.com(\/)?$"),
        deprecated=True,
    )

    TheNewYorker = Publisher(
        name="The New Yorker",
        domain="https://www.newyorker.com/",
        parser=TheNewYorkerParser,
        sources=[
            Sitemap("https://www.newyorker.com/sitemap.xml"),
            NewsMap("https://www.newyorker.com/feed/google-news-sitemap-feed/sitemap-google-news"),
        ],
    )

    Reuters = Publisher(
        name="Reuters",
        domain="https://www.reuters.com/",
        parser=ReutersParser,
        sources=[
            Sitemap("https://www.reuters.com/arc/outboundfeeds/sitemap-index/?outputType=xml"),
            NewsMap("https://www.reuters.com/arc/outboundfeeds/news-sitemap-index/?outputType=xml"),
        ],
        deprecated=True,
    )

    OccupyDemocrats = Publisher(
        name="Occupy Democrats",
        domain="https://occupydemocrats.com/",
        parser=OccupyDemocratsParser,
        sources=[
            Sitemap(
                url="https://occupydemocrats.com/sitemap.xml",
                sitemap_filter=inverse(regex_filter(r"post-sitemap")),
            )
        ],
        deprecated=True,
    )

    LATimes = Publisher(
        name="Los Angeles Times",
        domain="https://www.latimes.com/",
        parser=LATimesParser,
        sources=[
            Sitemap("https://www.latimes.com/sitemap.xml"),
            NewsMap("https://www.latimes.com/news-sitemap.xml"),
        ],
    )

    BusinessInsider = Publisher(
        name="Business Insider",
        domain="https://www.businessinsider.com/",
        parser=BusinessInsiderParser,
        sources=[
            NewsMap("https://www.businessinsider.com/sitemap/google-news.xml"),
            Sitemap("https://www.businessinsider.com/sitemap/2024-01.xml"),
        ],
    )

    RollingStone = Publisher(
        name="Rolling Stone",
        domain="https://www.rollingstone.com/",
        parser=RollingStoneParser,
        sources=[
            NewsMap("https://www.rollingstone.com/news-sitemap.xml"),
            Sitemap(
                "https://www.rollingstone.com/sitemap_index.xml",
                sitemap_filter=inverse(lor(regex_filter("/pmc_list-sitemap"), regex_filter("/post-sitemap"))),
            ),
        ],
    )

    VoiceOfAmerica = Publisher(
        name="Voice Of America",
        domain="https://www.voanews.com/",
        parser=VOAParser,
        url_filter=inverse(regex_filter(r"voanews\.com\/a\/[a-z-]+\/[0-9]+\.html")),
        sources=[
            Sitemap(
                "https://www.voanews.com/sitemap.xml",
                sitemap_filter=inverse(regex_filter(r"sitemap_[\d_]*\.xml\.gz")),
            ),
        ],
    )

    Wired = Publisher(
        name="Wired",
        domain="https://www.wired.com",
        parser=WiredParser,
        sources=[
            RSSFeed("https://www.wired.com/feed/rss"),
            NewsMap("https://www.wired.com/feed/google-latest-news/sitemap-google-news"),
            Sitemap("https://www.wired.com/sitemap.xml"),
            Sitemap("https://www.wired.com/sitemap-archive-1.xml"),
        ],
    )
