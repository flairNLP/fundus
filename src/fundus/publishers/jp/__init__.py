from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.jp.the_japan_news import TheJapanNewsParser
from fundus.publishers.jp.yomiuri_shimbun import YomiuriShimbunParser
from fundus.scraping.filter import regex_filter
from fundus.scraping.url import NewsMap, Sitemap


class JP(metaclass=PublisherGroup):
    default_languages = {"jp"}

    TheJapanNews = Publisher(
        name="The Japan News",
        domain="https://japannews.yomiuri.co.jp/",
        parser=TheJapanNewsParser,
        sources=[
            Sitemap(
                "https://japannews.yomiuri.co.jp/sitemap.xml",
                sitemap_filter=regex_filter(r"(sitemap-news|sitemap-root|category)"),
                languages={"en"},
            ),
            NewsMap(
                "https://japannews.yomiuri.co.jp/sitemap-news.xml",
                languages={"en"},
            ),
        ],
    )

    YomiuriShimbun = Publisher(
        name="Yomiuri Shimbun",
        domain="https://www.yomiuri.co.jp/",
        parser=YomiuriShimbunParser,
        sources=[
            Sitemap(
                "https://www.yomiuri.co.jp/sitemap.xml",
                sitemap_filter=regex_filter("sitemap-news-latest"),
            ),
            NewsMap("https://www.yomiuri.co.jp/sitemap-news-latest.xml"),
        ],
    )
