from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .asahi_shimbun import AsahiShimbunParser
from .mainichi_shimbun import MainichiShimbunParser
from .nikkan_geadai import NikkanGeadaiParser
from .nikkei import NikkeiParser
from .sankei_shimbun import SankeiShimbunParser
from .the_japan_news import TheJapanNewsParser
from .tokyo_chunichi_shimbun import TokyoChunichiShimbunParser
from .yomiuri_shimbun import YomiuriShimbunParser


class JP(metaclass=PublisherGroup):
    default_language = "ja"

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
        deprecated=True,
    )

    SankeiShimbun = Publisher(
        name="Sankei Shimbun",
        domain="https://www.sankei.com/",
        parser=SankeiShimbunParser,
        sources=[
            # The Google sitemap https://www.sankei.com/feeds/google-sitemapindex/ is included here as well
            NewsMap("https://www.sankei.com/feeds/sitemapindex-category/?outputType=xml"),
        ],
    )

    NikkanGeadai = Publisher(
        name="Nikkan Geadai",
        domain="https://www.nikkan-gendai.com/",
        parser=NikkanGeadaiParser,
        sources=[
            Sitemap(
                "https://www.nikkan-gendai.com/sitemap.xml",
                reverse=True,
                sitemap_filter=inverse(regex_filter(r"type=articles")),
            )
        ],
    )
