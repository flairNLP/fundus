from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.publishers.tr.ntvtr import NTVTRParser
from fundus.scraping.filter import regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap


class TR(PublisherEnum):
    NTVTR = PublisherSpec(
        name="NTVTR",
        domain="https://www.ntv.com.tr/",
        parser=NTVTRParser,
        sources=[
            RSSFeed("https://www.ntv.com.tr/gundem.rss"),
            NewsMap("https://www.ntv.com.tr/sitemaps/news-sitemap.xml"),
            Sitemap("https://www.ntv.com.tr/sitemaps", sitemap_filter=regex_filter("news-sitemap.xml")),
        ],
    )
