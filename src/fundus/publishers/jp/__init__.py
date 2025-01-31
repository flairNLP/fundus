from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.jp.asahi_shimbun import AsahiShimbunParser
from fundus.publishers.jp.mainichi_shimbun import MainichiShimbunParser
from fundus.publishers.jp.nikkei import NikkeiParser
from fundus.publishers.jp.the_japan_news import TheJapanNewsParser
from fundus.publishers.jp.tokyo_chunichi_shimbun import TokyoChunichiShimbunParser
from fundus.publishers.jp.yomiuri_shimbun import YomiuriShimbunParser
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap


class JP(metaclass=PublisherGroup):
    TheJapanNews = Publisher(
        name="The Japan News",
        domain="https://japannews.yomiuri.co.jp/",
        parser=TheJapanNewsParser,
        sources=[
            Sitemap(
                "https://japannews.yomiuri.co.jp/sitemap.xml",
                sitemap_filter=regex_filter(r"(sitemap-news|sitemap-root|category)"),
            ),
            NewsMap("https://japannews.yomiuri.co.jp/sitemap-news.xml"),
        ],
    )

    YomiuriShimbun = Publisher(
        name="Yomiuri Shimbun",
        domain="https://www.yomiuri.co.jp/",
        parser=YomiuriShimbunParser,
        sources=[
            Sitemap("https://www.yomiuri.co.jp/sitemap.xml", sitemap_filter=regex_filter("sitemap-news-latest")),
            NewsMap("https://www.yomiuri.co.jp/sitemap-news-latest.xml"),
        ],
    )

    AsahiShimbun = Publisher(
        name="Asahi Shimbun",
        domain="https://www.asahi.com/",
        parser=AsahiShimbunParser,
        sources=[NewsMap("https://www.asahi.com/sitemap.xml")],
    )

    TokyoShimbun = Publisher(
        name="Tokyo Shimbun",
        domain="https://www.tokyo-np.co.jp/",
        parser=TokyoChunichiShimbunParser,
        sources=[NewsMap("https://www.tokyo-np.co.jp/sitemap.xml")],
    )

    ChunichiShimbun = Publisher(
        name="Chunichi Shimbun",
        domain="https://www.chunichi.co.jp/",
        parser=TokyoChunichiShimbunParser,
        sources=[NewsMap("https://www.chunichi.co.jp/sitemap.xml")],
    )

    MainichiShimbun = Publisher(
        name="Mainichi Shimbun",
        domain="https://mainichi.jp/",
        parser=MainichiShimbunParser,
        sources=[
            RSSFeed("https://mainichi.jp/rss/etc/mainichi-flash.rss"),
        ],
    )

    Nikkei = Publisher(
        name="The Nikkei",
        domain="https://www.nikkei.com/",
        parser=NikkeiParser,
        sources=[
            NewsMap(
                "https://www.nikkei.com/sitemap.xml",
                sitemap_filter=inverse(regex_filter(r"[a-z]*\.sitemap\.xml$")),
            )
        ],
    )
