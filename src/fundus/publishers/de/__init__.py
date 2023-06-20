from datetime import datetime

from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.filter import regex_filter
from fundus.scraping.html import NewsMap, RSSFeed, Sitemap

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
        sources=[
            RSSFeed("https://www.welt.de/feeds/latest.rss"),
            Sitemap("https://www.welt.de/sitemaps/sitemap/sitemap.xml"),
            NewsMap("https://www.welt.de/sitemaps/newssitemap/newssitemap.xml"),
        ],
        url_filter=regex_filter("/Anlegertipps-|/videos[0-9]{2}"),
        parser=DieWeltParser,
    )

    MDR = PublisherSpec(
        name="Mitteldeutscher Rundfunk (MDR)",
        domain="https://www.mdr.de/",
        sources=[
            RSSFeed("https://www.mdr.de/nachrichten/index-rss.xml"),
            Sitemap("https://www.mdr.de/sitemap-index-100.xml"),
            NewsMap("https://www.mdr.de/news-sitemap.xml"),
        ],
        parser=MDRParser,
    )

    FAZ = PublisherSpec(
        name="Frankfurter Allgemeine Zeitung",
        domain="https://www.faz.net/",
        sources=[
            RSSFeed("https://www.faz.net/rss/aktuell"),
            RSSFeed("https://www.faz.net/rss/aktuell/politik"),
            RSSFeed("https://www.faz.net/rss/aktuell/sport"),
            RSSFeed("https://www.faz.net/rss/aktuell/wirtschaft/"),
            RSSFeed("https://www.faz.net/rss/aktuell/gesellschaft/"),
            Sitemap("https://www.faz.net/sitemap-index.xml"),
            NewsMap("https://www.faz.net/sitemap-news.xml"),
        ],
        parser=FAZParser,
    )

    Focus = PublisherSpec(
        name="Focus Online",
        domain="https://www.focus.de/",
        sources=[RSSFeed("https://rss.focus.de/fol/XML/rss_folnews.xml")],
        parser=FocusParser,
    )

    Merkur = PublisherSpec(
        name="Münchner Merkur",
        domain="https://www.merkur.de/",
        sources=[
            RSSFeed("https://www.merkur.de/welt/rssfeed.rdf"),
            Sitemap("https://www.merkur.de/sitemap-index.xml"),
            NewsMap("https://www.merkur.de/news.xml"),
        ],
        parser=MerkurParser,
    )

    SZ = PublisherSpec(
        name="Süddeutsche Zeitung",
        domain="https://www.sueddeutsche.de/",
        sources=[RSSFeed("https://rss.sueddeutsche.de/alles")],
        parser=SZParser,
    )

    SpiegelOnline = PublisherSpec(
        name="Spiegel Online",
        domain="https://www.spiegel.de/",
        sources=[
            RSSFeed("https://www.spiegel.de/schlagzeilen/index.rss"),
            Sitemap("https://www.spiegel.de/sitemap.xml"),
            NewsMap("https://www.spiegel.de/sitemaps/news-de.xml"),
        ],
        parser=SPONParser,
    )

    DieZeit = PublisherSpec(
        name="Die Zeit",
        domain="https://www.zeit.de/",
        sources=[
            RSSFeed("https://newsfeed.zeit.de/news/index"),
            Sitemap("https://www.zeit.de/gsitemaps/index.xml"),
            NewsMap(
                f"https://www.zeit.de/gsitemaps/index.xml?date={datetime.now().strftime('%Y-%m-%d')}&unit=days&period=1"
            ),
        ],
        request_header={"user-agent": "Googlebot"},
        url_filter=regex_filter(
            "|/zett/|/angebote/|/kaenguru-comics/|/administratives/|/index(?!.)|/elbvertiefung-[0-9]{2}-[0-9]{2}"
        ),
        parser=DieZeitParser,
    )

    BerlinerZeitung = PublisherSpec(
        name="Berliner Zeitung",
        domain="https://www.berliner-zeitung.de/",
        sources=[
            RSSFeed("https://www.berliner-zeitung.de/feed.xml"),
            Sitemap("https://www.berliner-zeitung.de/sitemap.xml"),
            NewsMap("https://www.berliner-zeitung.de/news-sitemap.xml"),
        ],
        url_filter=regex_filter("/news/"),
        parser=BerlinerZeitungParser,
    )

    Tagesschau = PublisherSpec(
        name="Tagesschau",
        domain="https://www.tagesschau.de/",
        sources=[RSSFeed("https://www.tagesschau.de/xml/rss2/")],
        parser=TagesschauParser,
    )

    DW = PublisherSpec(
        name="Deutsche Welle",
        domain="https://www.dw.com/",
        sources=[
            RSSFeed("https://rss.dw.com/xml/rss-de-all"),
            Sitemap("https://www.dw.com/de/article-sitemap.xml"),
            NewsMap("https://www.dw.com/de/news-sitemap.xml"),
        ],
        parser=DWParser,
    )
    Stern = PublisherSpec(
        name="Stern",
        domain="https://www.stern.de/",
        sources=[RSSFeed("https://www.stern.de/feed/standard/alle-nachrichten/")],
        parser=SternParser,
    )

    NTV = PublisherSpec(
        name="N-Tv",
        domain="https://www.ntv.de/",
        sources=[NewsMap("https://www.n-tv.de/news.xml"), Sitemap("https://www.n-tv.de/sitemap.xml")],
        parser=NTVParser,
    )

    NDR = PublisherSpec(
        name="Norddeutscher Rundfunk (NDR)",
        domain="https://www.ndr.de/",
        sources=[
            NewsMap("https://www.ndr.de/sitemap112-newssitemap.xml"),
            Sitemap("https://www.ndr.de/sitemap112-sitemap.xml"),
        ],
        parser=NDRParser,
        url_filter=regex_filter("podcast[0-9]{4}|/index.html"),
    )

    Taz = PublisherSpec(
        name="Die Tageszeitung (taz)",
        domain="https://www.taz.de/",
        sources=[NewsMap("https://taz.de/sitemap-google-news.xml"), Sitemap("https://taz.de/sitemap-index.xml")],
        parser=TazParser,
    )

    Bild = PublisherSpec(
        name="Bild",
        domain="https://www.bild.de/",
        sources=[RSSFeed("https://www.bild.de/rssfeeds/vw-neu/vw-neu-32001674,view=rss2.bild.xml")],
        parser=BildParser,
    )
