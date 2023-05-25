from datetime import datetime

from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.filter import regex_filter

from .berliner_zeitung import BerlinerZeitungParser
from .bild import BildParser
from .die_welt import DieWeltParser
from .die_zeit import DieZeitParser
from .dw import DWParser
from .faz import FAZParser
from .focus import FocusParser
from .mdr import MDRParser
from .merkur import MerkurParser
from .ndr import NDRParser
from .ntv import NTVParser
from .spon import SPONParser
from .stern import SternParser
from .sz import SZParser
from .tagesschau import TagesschauParser
from .taz import TazParser


# noinspection PyPep8Naming
class DE(PublisherEnum):
    DieWelt = PublisherSpec(
        name="Die Welt",
        domain="https://www.welt.de/",
        rss_feeds=["https://www.welt.de/feeds/latest.rss"],
        sitemaps=["https://www.welt.de/sitemaps/sitemap/sitemap.xml"],
        news_map="https://www.welt.de/sitemaps/newssitemap/newssitemap.xml",
        parser=DieWeltParser,
    )

    MDR = PublisherSpec(
        name="Mitteldeutscher Rundfunk (MDR)",
        domain="https://www.mdr.de/",
        rss_feeds=["https://www.mdr.de/nachrichten/index-rss.xml"],
        sitemaps=["https://www.mdr.de/sitemap-index-100.xml"],
        news_map="https://www.mdr.de/news-sitemap.xml",
        parser=MDRParser,
    )

    FAZ = PublisherSpec(
        name="Frankfurter Allgemeine Zeitung",
        domain="https://www.faz.net/",
        rss_feeds=[
            "https://www.faz.net/rss/aktuell",
            "https://www.faz.net/rss/aktuell/politik",
            "https://www.faz.net/rss/aktuell/sport",
            "https://www.faz.net/rss/aktuell/wirtschaft/",
            "https://www.faz.net/rss/aktuell/gesellschaft/",
        ],
        sitemaps=["https://www.faz.net/sitemap-index.xml"],
        news_map="https://www.faz.net/sitemap-news.xml",
        parser=FAZParser,
    )

    Focus = PublisherSpec(
        name="Focus Online",
        domain="https://www.focus.de/",
        rss_feeds=["https://rss.focus.de/fol/XML/rss_folnews.xml"],
        parser=FocusParser,
    )

    Merkur = PublisherSpec(
        name="Münchner Merkur",
        domain="https://www.merkur.de/",
        rss_feeds=["https://www.merkur.de/welt/rssfeed.rdf"],
        sitemaps=["https://www.merkur.de/sitemap-index.xml"],
        news_map="https://www.merkur.de/news.xml",
        parser=MerkurParser,
    )

    SZ = PublisherSpec(
        name="Süddeutsche Zeitung",
        domain="https://www.sueddeutsche.de/",
        rss_feeds=["https://rss.sueddeutsche.de/alles"],
        parser=SZParser,
    )

    SpiegelOnline = PublisherSpec(
        name="Spiegel Online",
        domain="https://www.spiegel.de/",
        rss_feeds=["https://www.spiegel.de/schlagzeilen/index.rss"],
        sitemaps=["https://www.spiegel.de/sitemap.xml"],
        news_map="https://www.spiegel.de/sitemaps/news-de.xml",
        parser=SPONParser,
    )

    DieZeit = PublisherSpec(
        name="Die Zeit",
        domain="https://www.sueddeutsche.de/",
        rss_feeds=["https://newsfeed.zeit.de/news/index"],
        sitemaps=["https://www.zeit.de/gsitemaps/index.xml"],
        news_map=f"https://www.zeit.de/gsitemaps/index.xml?date="
        f'{datetime.now().strftime("%Y-%m-%d")}&unit=days&period=1',
        parser=DieZeitParser,
    )

    BerlinerZeitung = PublisherSpec(
        name="Berliner Zeitung",
        domain="https://www.berliner-zeitung.de/",
        rss_feeds=["https://www.berliner-zeitung.de/feed.xml"],
        sitemaps=["https://www.berliner-zeitung.de/sitemap.xml"],
        news_map="https://www.berliner-zeitung.de/news-sitemap.xml",
        parser=BerlinerZeitungParser,
    )

    Tagesschau = PublisherSpec(
        name="Tagesschau",
        domain="https://www.tagesschau.de/",
        rss_feeds=["https://www.tagesschau.de/xml/rss2/"],
        parser=TagesschauParser,
    )

    DW = PublisherSpec(
        name="Deutsche Welle",
        domain="https://www.dw.com/",
        rss_feeds=["https://rss.dw.com/xml/rss-de-all"],
        sitemaps=["https://www.dw.com/de/article-sitemap.xml"],
        news_map="https://www.dw.com/de/news-sitemap.xml",
        parser=DWParser,
    )
    Stern = PublisherSpec(
        name="Stern",
        domain="https://www.stern.de/",
        rss_feeds=["https://www.stern.de/feed/standard/alle-nachrichten/"],
        parser=SternParser,
    )

    NTV = PublisherSpec(
        name="N-Tv",
        domain="https://www.ntv.de/",
        news_map="https://www.n-tv.de/news.xml",
        sitemaps=["https://www.n-tv.de/sitemap.xml"],
        parser=NTVParser,
    )

    NDR = PublisherSpec(
        name="Norddeutscher Rundfunk (NDR)",
        domain="https://www.ndr.de/",
        news_map="https://www.ndr.de/sitemap112-newssitemap.xml",
        sitemaps=["https://www.ndr.de/sitemap112-sitemap.xml"],
        parser=NDRParser,
        url_filter=regex_filter("podcast[0-9]{4}|/index.html"),
    )

    Taz = PublisherSpec(
        name="Die Tageszeitung (taz)",
        domain="https://www.taz.de/",
        news_map="https://taz.de/sitemap-google-news.xml",
        sitemaps=["https://taz.de/sitemap-index.xml"],
        parser=TazParser,
    )

    Bild = PublisherSpec(
        name="Bild",
        domain="https://www.bild.de/",
        rss_feeds=["https://www.bild.de/rssfeeds/vw-neu/vw-neu-32001674,view=rss2.bild.xml"],
        parser=BildParser,
    )
