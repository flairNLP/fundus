from datetime import datetime
from typing import Optional

from dateutil.rrule import MONTHLY, YEARLY, rrule

from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from ..shared import EuronewsParser
from .berliner_zeitung import BerlinerZeitungParser
from .bild import BildParser
from .boersenzeitung import BoersenZeitungParser
from .br import BRParser
from .braunschweiger_zeitung import BSZParser
from .business_insider_de import BusinessInsiderDEParser
from .die_welt import DieWeltParser
from .die_zeit import DieZeitParser
from .dw import DWParser
from .faz import FAZParser
from .focus import FocusParser
from .frankfurter_rundschau import FrankfurterRundschauParser
from .freiepresse import FreiePresseParser
from .gamestar import GamestarParser
from .hamburger_abendblatt import HamburgerAbendblattParser
from .hessenschau import HessenschauParser
from .junge_welt import JungeWeltParser
from .kicker import KickerParser
from .mdr import MDRParser
from .merkur import MerkurParser
from .morgenpost_berlin import BerlinerMorgenpostParser
from .motorsport_magazin import MotorSportMagazinParser
from .mz import MitteldeutscheZeitungParser
from .ndr import NDRParser
from .netzpolitik_org import NetzpolitikOrgParser
from .ntv import NTVParser
from .postillon import PostillonParser
from .rheinische_post import RheinischePostParser
from .rn import RuhrNachrichtenParser
from .spon import SPONParser
from .sportschau import SportSchauParser
from .stern import SternParser
from .sz import SZParser
from .tagesschau import TagesschauParser
from .tagesspiegel import TagesspiegelParser
from .taz import TazParser
from .vogue_de import VogueDEParser
from .waz import WAZParser
from .wdr import WDRParser
from .winfuture import WinfutureParser
from .zdf import ZDFParser


# noinspection PyPep8Naming
class DE(PublisherEnum):
    SportSchau = PublisherSpec(
        name="Sportschau",
        domain="https://www.sportschau.de/",
        parser=SportSchauParser,
        sources=[
            RSSFeed("https://www.sportschau.de/index~rss2.xml"),
            Sitemap("https://www.sportschau.de/index~sitemap_p-0.xml"),
            NewsMap("https://www.sportschau.de/kompakt-sp-100~news.xml"),
        ],
        url_filter=inverse(regex_filter("sportschau.de")),
    )

    NetzpolitikOrg = PublisherSpec(
        name="netzpolitik.org",
        domain="https://netzpolitik.org/",
        sources=[
            Sitemap(
                "https://netzpolitik.org/sitemap.xml", sitemap_filter=inverse(regex_filter("sitemap-posttype-post"))
            ),
            RSSFeed("https://netzpolitik.org/feed/"),
        ],
        parser=NetzpolitikOrgParser,
    )

    BerlinerMorgenpost = PublisherSpec(
        name="Berliner Morgenpost",
        domain="https://www.morgenpost.de/",
        sources=[NewsMap("https://www.morgenpost.de/sitemaps/news.xml")]
        + [
            Sitemap(f"https://www.morgenpost.de/sitemaps/archive/sitemap-{d.year}-{str(d.month).zfill(2)}-p00.xml.gz")
            for d in reversed(list(rrule(MONTHLY, dtstart=datetime(2003, 2, 1), until=datetime.now())))
        ],
        parser=BerlinerMorgenpostParser,
    )

    HamburgerAbendblatt = PublisherSpec(
        name="Hamburger Abendblatt",
        domain="https://www.abendblatt.de/",
        sources=[
            RSSFeed("https://www.abendblatt.de/rss"),
            NewsMap("https://www.abendblatt.de/sitemaps/news.xml"),
        ]
        + [
            Sitemap(f"https://www.abendblatt.de/sitemaps/archive/sitemap-{d.year}-{str(d.month).zfill(2)}-p00.xml.gz")
            for d in reversed(list(rrule(MONTHLY, dtstart=datetime(2000, 4, 1), until=datetime.today())))
        ],
        parser=HamburgerAbendblattParser,
    )

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
        # Focus blocks access for all user-agents including the term 'bot'
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
        request_header={"User-Agent": "Googlebot"},
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
        request_header={"user-agent": "Googlebot"},
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
        sources=[
            NewsMap("https://taz.de/sitemap-google-news.xml"),
            Sitemap("https://taz.de/sitemap-index.xml"),
        ],
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
            for d in list(rrule(MONTHLY, dtstart=datetime(2005, 12, 1), until=datetime.now()))
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

    WinFuture = PublisherSpec(
        name="WinFuture",
        domain="https://winfuture.de/",
        sources=[
            RSSFeed("https://static.winfuture.de/feeds/WinFuture-News-rss2.0.xml"),
            NewsMap("https://winfuture.de/sitemap-latest-news.xml.gz"),
            Sitemap("https://winfuture.de/sitemap.xml", sitemap_filter=inverse(regex_filter("sitemap-news"))),
        ],
        url_filter=regex_filter("https:////winfuture/.de//news*"),
        parser=WinfutureParser,
    )

    JungeWelt = PublisherSpec(
        name="Junge Welt",
        domain="https://www.jungewelt.de/",
        sources=[
            RSSFeed("https://www.jungewelt.de/feeds/newsticker.rss"),
        ],
        parser=JungeWeltParser,
    )

    Tagesspiegel = PublisherSpec(
        name="Tagesspiegel",
        domain="https://www.tagesspiegel.de/",
        sources=[
            NewsMap("https://www.tagesspiegel.de/news.xml"),
        ]
        + [
            Sitemap(f"https://www.tagesspiegel.de/contentexport/static/sitemap-index_{date.year}.xml")
            for date in reversed(list(rrule(YEARLY, dtstart=datetime(1996, 1, 1), until=datetime.today())))
        ],
        parser=TagesspiegelParser,
    )

    EuronewsDE = PublisherSpec(
        name="Euronews (DE)",
        domain="https://de.euronews.com/",
        sources=[
            Sitemap("https://de.euronews.com/sitemaps/de/articles.xml"),
            NewsMap("https://de.euronews.com/sitemaps/de/latest-news.xml"),
        ],
        parser=EuronewsParser,
    )

    Hessenschau = PublisherSpec(
        name="Hessenschau",
        domain="https://www.hessenschau.de/",
        sources=[
            RSSFeed("https://www.hessenschau.de/index.rss"),
            Sitemap("https://www.hessenschau.de/indexsitemap.nc.xml"),
            Sitemap("https://www.hessenschau.de/sitemap.nc.xml"),
        ],
        parser=HessenschauParser,
    )

    WDR = PublisherSpec(
        name="Westdeutscher Rundfunk",
        domain="https://www1.wdr.de/",
        sources=[RSSFeed("https://www1.wdr.de/uebersicht-100.feed")],
        parser=WDRParser,
    )

    BR = PublisherSpec(
        name="Bayerischer Rundfunk (BR)",
        domain="https://www.br.de/",
        sources=[
            Sitemap("https://www.br.de/sitemapIndex.xml"),
            NewsMap("https://www.br.de/nachrichten/sitemaps/news.xml"),
        ],
        parser=BRParser,
    )

    ZDF = PublisherSpec(
        name="zdfHeute",
        domain="https://www.zdf.de/",
        sources=[
            Sitemap("https://www.zdf.de/sitemap.xml", reverse=True),
            NewsMap("https://www.zdf.de/news-sitemap.xml"),
            RSSFeed("https://www.zdf.de/rss/zdf/nachrichten"),
        ],
        parser=ZDFParser,
    )

    MotorSportMagazin = PublisherSpec(
        name="MotorSport Magazin",
        domain="https://www.motorsport-magazin.com/",
        sources=[
            RSSFeed("https://www.motorsport-magazin.com/rss/alle-rennserien.xml"),
            Sitemap("https://www.motorsport-magazin.com/sitemap.xml"),
        ],
        parser=MotorSportMagazinParser,
    )

    Postillon = PublisherSpec(
        name="Postillon",
        domain="https://www.der-postillon.com/",
        sources=[
            RSSFeed("https://follow.it/der-postillon-abo"),
            Sitemap("https://www.der-postillon.com/sitemap.xml"),
        ],
        parser=PostillonParser,
    )

    Kicker = PublisherSpec(
        name="Kicker",
        domain="https://www.kicker.de/",
        sources=[
            RSSFeed("https://newsfeed.kicker.de/news/aktuell"),
            Sitemap(
                "https://leserservice.kicker.de/sitemap_0.xml", sitemap_filter=regex_filter("leserservice.kicker.de")
            ),
            NewsMap("https://newsfeed.kicker.de/googlesitemapnews.xml"),
        ],
        url_filter=regex_filter("/slideshow|/video"),
        parser=KickerParser,
    )

    FrankfurterRundschau = PublisherSpec(
        name="Frankfurter Rundschau",
        domain="https://www.fr.de",
        sources=[
            RSSFeed("https://fr.de/rssfeed.rdf"),
            Sitemap("https://www.fr.de/sitemap-index.xml"),
            NewsMap("https://www.fr.de/news.xml"),
        ],
        parser=FrankfurterRundschauParser,
    )

    BoersenZeitung = PublisherSpec(
        name="Börsen-Zeitung",
        domain="https://www.boersen-zeitung.de",
        sources=[
            NewsMap("https://www.boersen-zeitung.de/sitemap/news.xml.gz"),
            Sitemap(
                "https://www.boersen-zeitung.de/sitemap/index.xml.gz", sitemap_filter=regex_filter("/sitemap-0.xml.gz")
            ),
        ],
        parser=BoersenZeitungParser,
    )

    VogueDE = PublisherSpec(
        name="Vogue",
        domain="https://www.vogue.de/",
        sources=[
            RSSFeed("https://www.vogue.de/feed/rss"),
            NewsMap("https://www.vogue.de/feed/sitemap-news/sitemap-google-news"),
            Sitemap("https://www.vogue.de/sitemap.xml"),
        ],
        parser=VogueDEParser,
    )

    MitteldeutscheZeitung = PublisherSpec(
        name="Mitteldeutsche Zeitung",
        domain="https://www.mz.de/",
        sources=[
            Sitemap("https://www.mz.de/sitemaps/sitemap-ressort-index.xml"),
            NewsMap("https://www.mz.de/sitemaps/newssitemap-index.xml"),
        ],
        parser=MitteldeutscheZeitungParser,
    )

    FreiePresse = PublisherSpec(
        name="FreiePresse",
        domain="https://www.freiepresse.de/",
        sources=[
            RSSFeed("https://www.freiepresse.de/rss/rss_chemnitz.php"),
            RSSFeed("https://www.freiepresse.de/rss/rss_erzgebirge.php"),
            RSSFeed("https://www.freiepresse.de/rss/rss_mittelsachsen.php"),
            RSSFeed("https://www.freiepresse.de/rss/rss_vogtland.php"),
            RSSFeed("https://www.freiepresse.de/rss/rss_zwickau.php"),
            RSSFeed("https://www.freiepresse.de/rss/rss_politik.php"),
            RSSFeed("https://www.freiepresse.de/rss/rss_wirtschaft.php"),
            RSSFeed("https://www.freiepresse.de/rss/rss_kultur.php"),
            RSSFeed("https://www.freiepresse.de/rss/rss_sport.php"),
            RSSFeed("https://www.freiepresse.de/rss/rss_sachsen.php"),
            RSSFeed("https://www.freiepresse.de/rss/rss_regional.php"),
            Sitemap("https://www.freiepresse.de/sitemaps/articles_last2years.xml", reverse=True),
        ],
        parser=FreiePresseParser,
    )

    RuhrNachrichten = PublisherSpec(
        name="Ruhr Nachrichten",
        domain="https://www.ruhrnachrichten.de/",
        sources=[
            RSSFeed("https://www.ruhrnachrichten.de/service/feed/"),
            NewsMap("https://www.ruhrnachrichten.de/news-sitemap.xml"),
            Sitemap(
                "https://www.ruhrnachrichten.de/sitemap_index.xml",
                reverse=True,
                sitemap_filter=inverse(regex_filter("post-sitemap")),
            ),
        ],
        parser=RuhrNachrichtenParser,
    )

    Gamestar = PublisherSpec(
        name="Gamestar",
        domain="https://www.gamestar.de/",
        sources=[
            NewsMap("https://www.gamestar.de/sitemapnews.xml"),
            Sitemap("https://www.gamestar.de/artikel_archiv_index.xml"),
        ],
        parser=GamestarParser,
    )
