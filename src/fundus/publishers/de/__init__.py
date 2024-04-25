from datetime import datetime

from dateutil.rrule import MONTHLY, rrule

from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.filter import regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .berliner_zeitung import BerlinerZeitungParser
from .bild import BildParser
from .braunschweiger_zeitung import BSZParser
from .business_insider_de import BusinessInsiderDEParser
from .die_welt import DieWeltParser
from .die_zeit import DieZeitParser
from .dw import DWParser
from .faz import FAZParser
from .focus import FocusParser
from .mdr import MDRParser
from .merkur import MerkurParser
from .ndr import NDRParser
from .ntv import NTVParser
from .rbb24 import RBB24Parser
from .rheinische_post import RheinischePostParser
from .spon import SPONParser
from .stern import SternParser
from .sz import SZParser
from .tagesschau import TagesschauParser
from .taz import TazParser
from .waz import WAZParser


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
        # Focus blocks access for all user-agents including the term 'Bot'
        request_header={"user-agent": "Fundus"},
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
            Sitemap("https://www.zeit.de/gsitemaps/index.xml", reverse=True),
            NewsMap(
                f"https://www.zeit.de/gsitemaps/index.xml?date={datetime.now().strftime('%Y-%m-%d')}&unit=days&period=1"
            ),
        ],
        url_filter=regex_filter(
            "/zett/|/angebote/|/kaenguru-comics/|/administratives/|/index(?!.)|/elbvertiefung-[0-9]{2}-[0-9]{2}"
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
        domain="https://www.n-tv.de/",
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
        domain="https://taz.de/",
        sources=[NewsMap("https://taz.de/sitemap-google-news.xml"), Sitemap("https://taz.de/sitemap-index.xml"),],
        parser=TazParser,
    )

    Bild = PublisherSpec(
        name="Bild",
        domain="https://www.bild.de/",
        sources=[
            RSSFeed("https://www.bild.de/rssfeeds/vw-neu/vw-neu-32001674,view=rss2.bild.xml"),
            NewsMap("https://www.bild.de/sitemap-news.xml"),
            Sitemap("https://www.bild.de/sitemap-index.xml"),
        ],
        parser=BildParser,
    )

    WAZ = PublisherSpec(
        name="Westdeutsche Allgemeine Zeitung (WAZ)",
        domain="https://www.waz.de/",
        sources=[NewsMap("https://www.waz.de/sitemaps/news.xml")],
        parser=WAZParser,
    )

    BSZ = PublisherSpec(
        name="Braunschweiger Zeitung",
        domain="https://www.braunschweiger-zeitung.de/",
        sources=[
            RSSFeed("https://www.braunschweiger-zeitung.de/rss"),
            NewsMap("https://www.braunschweiger-zeitung.de/sitemaps/news.xml"),
        ]
        + [
            Sitemap(
                f"https://www.braunschweiger-zeitung.de/sitemaps/archive/sitemap-{d.year}-{str(d.month).zfill(2)}-p00.xml.gz"
            )
            for d in reversed(list(rrule(MONTHLY, dtstart=datetime(2016, 9, 1), until=datetime.now())))
        ],
        parser=BSZParser,
    )

    BusinessInsiderDE = PublisherSpec(
        name="Business Insider DE",
        domain="https://www.businessinsider.de/",
        sources=[
            NewsMap("https://www.businessinsider.de/news-sitemap.xml"),
            Sitemap("https://www.businessinsider.de/sitemap_index.xml"),
        ],
        parser=BusinessInsiderDEParser,
    )

    RheinischePost = PublisherSpec(
        name="Rheinische Post",
        domain="https://rp-online.de/",
        sources=[
            RSSFeed("https://rp-online.de/feed.rss"),
            NewsMap("https://rp-online.de/sitemap-news.xml"),
            Sitemap("https://rp-online.de/sitemap.xml"),
        ],
        parser=RheinischePostParser,
    )

    RBB24 = PublisherSpec(
        name="rbb|24",
        domain="https://www.rbb24.de/",
        sources=[RSSFeed("https://www.rbb24.de/aktuell/index.xml/feed=rss.xml")],
        parser=RBB24Parser,
    )
