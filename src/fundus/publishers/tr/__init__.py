from fundus.publishers.base_objects import PublisherGroup, Publisher
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .haberturk import HaberturkParser
from .ntvtr import NTVTRParser


class TR(PublisherGroup):
    Haberturk = Publisher(
        name="Haberturk",
        domain="https://www.haberturk.com/",
        sources=[
            Sitemap(
                "https://www.haberturk.com/sitemap.xml",
                sitemap_filter=inverse(regex_filter("news|special|posts|ozel_icerikler")),
                reverse=True,
            ),
            NewsMap("https://www.haberturk.com/sitemap_google_news.xml"),
        ],
        parser=HaberturkParser,
    )

    NTVTR = Publisher(
        name="NTVTR",
        domain="https://www.ntv.com.tr/",
        sources=[
            RSSFeed("https://www.ntv.com.tr/gundem.rss"),
            NewsMap("https://www.ntv.com.tr/sitemaps/news-sitemap.xml"),
            Sitemap("https://www.ntv.com.tr/sitemaps", sitemap_filter=regex_filter("news-sitemap.xml")),
        ],
        parser=NTVTRParser,
    )
