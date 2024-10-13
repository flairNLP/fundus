from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.jp.thejapannews import TheJapanNewsParser
from fundus.scraping.url import NewsMap, Sitemap


class JP(metaclass=PublisherGroup):
    TheJapanNews = Publisher(
        name="The Japan News",
        domain="https://japannews.yomiuri.co.jp/",
        parser=TheJapanNewsParser,
        sources=[
            Sitemap("https://japannews.yomiuri.co.jp/sitemap.xml"),
            NewsMap("https://japannews.yomiuri.co.jp/sitemap-news.xml"),
        ],
    )
