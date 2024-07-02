from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .haberturk import HaberturkParser
from .ntvtr import NTVTRParser


class TR(metaclass=PublisherGroup):
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
