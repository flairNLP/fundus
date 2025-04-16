from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .anadolu_ajansi import AnadoluAjansiParser
from .haberturk import HaberturkParser
from .ntvtr import NTVTRParser


class TR(metaclass=PublisherGroup):
    default_language = "tr"
    Haberturk = Publisher(
        name="Haberturk",
        domain="https://www.haberturk.com/",
        parser=HaberturkParser,
        sources=[
            Sitemap(
                "https://www.haberturk.com/sitemap.xml",
                sitemap_filter=inverse(regex_filter("news|special|posts|ozel_icerikler")),
                reverse=True,
            ),
            NewsMap("https://www.haberturk.com/sitemap_google_news.xml"),
        ],
    )

    NTVTR = Publisher(
        name="NTVTR",
        domain="https://www.ntv.com.tr/",
        parser=NTVTRParser,
        sources=[
            RSSFeed("https://www.ntv.com.tr/gundem.rss"),
            NewsMap("https://www.ntv.com.tr/sitemaps/news-sitemap.xml"),
            Sitemap("https://www.ntv.com.tr/sitemaps", sitemap_filter=regex_filter("news-sitemap.xml")),
        ],
    )

    AnadoluAjansi = Publisher(
        name="Anadolu Ajansı",
        domain="https://www.aa.com.tr/",
        parser=AnadoluAjansiParser,
        sources=[
            RSSFeed("https://www.aa.com.tr/tr/rss/default?cat=guncel"),
            RSSFeed("https://www.aa.com.tr/tr/teyithatti/rss/news?cat=gazze"),
            RSSFeed("https://www.aa.com.tr/tr/teyithatti/rss/news?cat=politika"),
            RSSFeed("https://www.aa.com.tr/tr/teyithatti/rss/news?cat=aktuel"),
            RSSFeed("https://www.aa.com.tr/tr/teyithatti/rss/news?cat=kultur-sanat"),
            RSSFeed("https://www.aa.com.tr/tr/teyithatti/rss/news?cat=bilim-teknoloji"),
            RSSFeed("https://www.aa.com.tr/tr/teyithatti/rss/news?cat=blog"),
            RSSFeed("https://www.aa.com.tr/tr/teyithatti/rss/news?cat=teyit-sozlugu"),
            RSSFeed("https://www.aa.com.tr/tr/teyithatti/rss/news?cat=ekonomi"),
            RSSFeed("https://www.aa.com.tr/tr/teyithatti/rss/news?cat=0"),
            RSSFeed("https://www.aa.com.tr/tr/teyithatti/rss/video"),
        ],
    )
