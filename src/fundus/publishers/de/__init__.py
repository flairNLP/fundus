from datetime import datetime

from dateutil.rrule import MONTHLY, YEARLY, rrule

from fundus.publishers.base_objects import Publisher, PublisherGroup
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
from .golem import GolemParser
from .hamburger_abendblatt import HamburgerAbendblattParser
from .heise import HeiseParser
from .hessenschau import HessenschauParser
from .junge_welt import JungeWeltParser
from .kicker import KickerParser
from .krautreporter import KrautreporterParser
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
class DE(metaclass=PublisherGroup):
    SportSchau = Publisher(
        name="Sportschau",
        domain="https://www.sportschau.de/",
        parser=SportSchauParser,
        sources=[
            RSSFeed("https://www.sportschau.de/index~rss2.xml", languages={"de"}),
            Sitemap("https://www.sportschau.de/index~sitemap_p-0.xml", languages={"de"}),
            NewsMap("https://www.sportschau.de/kompakt-sp-100~news.xml", languages={"de"}),
        ],
        url_filter=inverse(regex_filter("sportschau.de")),
    )

    NetzpolitikOrg = Publisher(
        name="netzpolitik.org",
        domain="https://netzpolitik.org/",
        parser=NetzpolitikOrgParser,
        sources=[
            Sitemap(
                "https://netzpolitik.org/sitemap.xml",
                sitemap_filter=inverse(regex_filter("sitemap-posttype-post")),
                languages={"de"},
            ),
            RSSFeed("https://netzpolitik.org/feed/", languages={"de"}),
        ],
    )

    BerlinerMorgenpost = Publisher(
        name="Berliner Morgenpost",
        domain="https://www.morgenpost.de/",
        parser=BerlinerMorgenpostParser,
        sources=[NewsMap("https://www.morgenpost.de/sitemaps/news.xml", languages={"de"})]
        + [
            Sitemap(
                f"https://www.morgenpost.de/sitemaps/archive/sitemap-{d.year}-{str(d.month).zfill(2)}-p00.xml.gz",
                languages={"de"},
            )
            for d in reversed(list(rrule(MONTHLY, dtstart=datetime(2003, 2, 1), until=datetime.now())))
        ],
    )

    HamburgerAbendblatt = Publisher(
        name="Hamburger Abendblatt",
        domain="https://www.abendblatt.de/",
        parser=HamburgerAbendblattParser,
        sources=[
            RSSFeed("https://www.abendblatt.de/rss", languages={"de"}),
            NewsMap("https://www.abendblatt.de/sitemaps/news.xml", languages={"de"}),
        ]
        + [
            Sitemap(
                f"https://www.abendblatt.de/sitemaps/archive/sitemap-{d.year}-{str(d.month).zfill(2)}-p00.xml.gz",
                languages={"de"},
            )
            for d in reversed(list(rrule(MONTHLY, dtstart=datetime(2000, 4, 1), until=datetime.today())))
        ],
    )

    DieWelt = Publisher(
        name="Die Welt",
        domain="https://www.welt.de/",
        parser=DieWeltParser,
        sources=[
            RSSFeed("https://www.welt.de/feeds/latest.rss", languages={"de"}),
            Sitemap("https://www.welt.de/sitemaps/sitemap/sitemap.xml", languages={"de"}),
            NewsMap("https://www.welt.de/sitemaps/newssitemap/newssitemap.xml", languages={"de"}),
        ],
        url_filter=regex_filter("/Anlegertipps-|/videos[0-9]{2}"),
    )

    MDR = Publisher(
        name="Mitteldeutscher Rundfunk (MDR)",
        domain="https://www.mdr.de/",
        parser=MDRParser,
        sources=[
            RSSFeed("https://www.mdr.de/nachrichten/index-rss.xml", languages={"de"}),
            Sitemap("https://www.mdr.de/sitemap-index-100.xml", languages={"de"}),
            NewsMap("https://www.mdr.de/news-sitemap.xml", languages={"de"}),
        ],
    )

    FAZ = Publisher(
        name="Frankfurter Allgemeine Zeitung",
        domain="https://www.faz.net/",
        parser=FAZParser,
        sources=[
            RSSFeed("https://www.faz.net/rss/aktuell", languages={"de"}),
            RSSFeed("https://www.faz.net/rss/aktuell/politik", languages={"de"}),
            RSSFeed("https://www.faz.net/rss/aktuell/sport", languages={"de"}),
            RSSFeed("https://www.faz.net/rss/aktuell/wirtschaft/", languages={"de"}),
            RSSFeed("https://www.faz.net/rss/aktuell/gesellschaft/", languages={"de"}),
            Sitemap("https://www.faz.net/sitemap-index.xml", languages={"de"}),
            NewsMap("https://www.faz.net/sitemap-news.xml", languages={"de"}),
        ],
    )

    Focus = Publisher(
        name="Focus Online",
        domain="https://www.focus.de/",
        parser=FocusParser,
        sources=[RSSFeed("https://rss.focus.de/fol/XML/rss_folnews.xml", languages={"de"})],
        request_header={"user-agent": "Fundus"},
    )

    Merkur = Publisher(
        name="Münchner Merkur",
        domain="https://www.merkur.de/",
        parser=MerkurParser,
        sources=[
            RSSFeed("https://www.merkur.de/welt/rssfeed.rdf", languages={"de"}),
            Sitemap("https://www.merkur.de/sitemap-index.xml", languages={"de"}),
            NewsMap("https://www.merkur.de/news.xml", languages={"de"}),
        ],
    )

    SZ = Publisher(
        name="Süddeutsche Zeitung",
        domain="https://www.sueddeutsche.de/",
        parser=SZParser,
        sources=[RSSFeed("https://rss.sueddeutsche.de/alles", languages={"de"})],
    )

    SpiegelOnline = Publisher(
        name="Spiegel Online",
        domain="https://www.spiegel.de/",
        parser=SPONParser,
        sources=[
            RSSFeed("https://www.spiegel.de/schlagzeilen/index.rss", languages={"de"}),
            Sitemap("https://www.spiegel.de/sitemap.xml", languages={"de"}),
            NewsMap("https://www.spiegel.de/sitemaps/news-de.xml", languages={"de"}),
        ],
        request_header={"User-Agent": "Googlebot"},
    )

    DieZeit = Publisher(
        name="Die Zeit",
        domain="https://www.zeit.de/",
        parser=DieZeitParser,
        sources=[
            RSSFeed("https://newsfeed.zeit.de/news/index", languages={"de"}),
            Sitemap("https://www.zeit.de/gsitemaps/index.xml", reverse=True, languages={"de"}),
            NewsMap(
                f"https://www.zeit.de/gsitemaps/index.xml?date={datetime.now().strftime('%Y-%m-%d')}&unit=days&period=1",
                languages={"de"},
            ),
        ],
        url_filter=regex_filter(
            "/zett/|/angebote/|/kaenguru-comics/|/administratives/|/index(?!.)|/elbvertiefung-[0-9]{2}-[0-9]{2}"
        ),
        request_header={"user-agent": "Googlebot"},
    )

    BerlinerZeitung = Publisher(
        name="Berliner Zeitung",
        domain="https://www.berliner-zeitung.de/",
        parser=BerlinerZeitungParser,
        sources=[
            RSSFeed("https://www.berliner-zeitung.de/feed.xml", languages={"de"}),
            Sitemap("https://www.berliner-zeitung.de/sitemap.xml", languages={"de"}),
            NewsMap("https://www.berliner-zeitung.de/news-sitemap.xml", languages={"de"}),
        ],
        url_filter=regex_filter("/news/"),
    )

    Tagesschau = Publisher(
        name="Tagesschau",
        domain="https://www.tagesschau.de/",
        parser=TagesschauParser,
        sources=[RSSFeed("https://www.tagesschau.de/xml/rss2/", languages={"de"})],
    )

    DW = Publisher(
        name="Deutsche Welle",
        domain="https://www.dw.com/",
        parser=DWParser,
        sources=[
            RSSFeed("https://rss.dw.com/xml/rss-de-all", languages={"de"}),
            Sitemap("https://www.dw.com/de/article-sitemap.xml", languages={"de"}),
            NewsMap("https://www.dw.com/de/news-sitemap.xml", languages={"de"}),
        ],
    )
    Stern = Publisher(
        name="Stern",
        domain="https://www.stern.de/",
        parser=SternParser,
        sources=[RSSFeed("https://www.stern.de/feed/standard/alle-nachrichten/", languages={"de"})],
    )

    NTV = Publisher(
        name="N-Tv",
        domain="https://www.n-tv.de/",
        parser=NTVParser,
        sources=[
            NewsMap("https://www.n-tv.de/news.xml", languages={"de"}),
            Sitemap(
                "https://www.n-tv.de/sitemap.xml", sitemap_filter=regex_filter("sitemap-sections"), languages={"de"}
            ),
        ],
    )

    NDR = Publisher(
        name="Norddeutscher Rundfunk (NDR)",
        domain="https://www.ndr.de/",
        parser=NDRParser,
        sources=[
            NewsMap("https://www.ndr.de/sitemap112-newssitemap.xml", languages={"de"}),
            Sitemap("https://www.ndr.de/sitemap112-sitemap.xml", languages={"de"}),
        ],
        url_filter=regex_filter("podcast[0-9]{4}|/index.html"),
    )

    Taz = Publisher(
        name="Die Tageszeitung (taz)",
        domain="https://taz.de/",
        parser=TazParser,
        sources=[
            NewsMap("https://taz.de/sitemap-google-news.xml", languages={"de"}),
            Sitemap("https://taz.de/sitemap-index.xml", languages={"de"}),
        ],
    )

    Heise = Publisher(
        name="Heise",
        domain="https://www.heise.de",
        sources=[
            RSSFeed("https://www.heise.de/rss/heise.rdf", languages={"de"}),
            Sitemap(
                "https://www.heise.de/sitemapindex.xml",
                sitemap_filter=inverse(regex_filter("/news/")),
                languages={"de"},
            ),
        ],
        parser=HeiseParser,
        query_parameter={"seite": "all"},
    )

    Bild = Publisher(
        name="Bild",
        domain="https://www.bild.de/",
        parser=BildParser,
        sources=[
            RSSFeed("https://www.bild.de/rssfeeds/vw-neu/vw-neu-32001674,view=rss2.bild.xml", languages={"de"}),
            NewsMap("https://www.bild.de/sitemap-news.xml", languages={"de"}),
            Sitemap("https://www.bild.de/sitemap-index.xml", languages={"de"}),
        ],
    )

    WAZ = Publisher(
        name="Westdeutsche Allgemeine Zeitung (WAZ)",
        domain="https://www.waz.de/",
        parser=WAZParser,
        sources=[NewsMap("https://www.waz.de/sitemaps/news.xml", languages={"de"})],
    )

    BSZ = Publisher(
        name="Braunschweiger Zeitung",
        domain="https://www.braunschweiger-zeitung.de/",
        parser=BSZParser,
        sources=[
            RSSFeed("https://www.braunschweiger-zeitung.de/rss", languages={"de"}),
            NewsMap("https://www.braunschweiger-zeitung.de/sitemaps/news.xml", languages={"de"}),
        ]
        + [
            Sitemap(
                f"https://www.braunschweiger-zeitung.de/sitemaps/archive/sitemap-{d.year}-{str(d.month).zfill(2)}-p00.xml.gz",
                languages={"de"},
            )
            for d in list(rrule(MONTHLY, dtstart=datetime(2005, 12, 1), until=datetime.now()))
        ],
    )

    BusinessInsiderDE = Publisher(
        name="Business Insider DE",
        domain="https://www.businessinsider.de/",
        parser=BusinessInsiderDEParser,
        sources=[
            RSSFeed("https://www.businessinsider.de/feed/businessinsider-alle-artikel", languages={"de"}),
            NewsMap("https://www.businessinsider.de/news-sitemap.xml", languages={"de"}),
            Sitemap(
                "https://www.businessinsider.de/sitemap_index.xml",
                sitemap_filter=inverse(regex_filter("post-sitemap")),
                reverse=True,
                languages={"de"},
            ),
        ],
    )

    RheinischePost = Publisher(
        name="Rheinische Post",
        domain="https://rp-online.de/",
        parser=RheinischePostParser,
        sources=[
            RSSFeed("https://rp-online.de/feed.rss", languages={"de"}),
            NewsMap("https://rp-online.de/sitemap-news.xml", languages={"de"}),
            Sitemap("https://rp-online.de/sitemap.xml", languages={"de"}),
        ],
    )

    Golem = Publisher(
        name="Golem",
        domain="https://www.golem.de/",
        sources=[
            RSSFeed("https://www.golem.de/rss", languages={"de"}),
            NewsMap("https://www.golem.de/news/gsitemap-2404.xml", languages={"de"}),
            Sitemap("https://www.golem.de/gsiteindex.xml", languages={"de"}),
        ],
        request_header={"User-Agent": "Googlebot"},
        parser=GolemParser,
    )

    WinFuture = Publisher(
        name="WinFuture",
        domain="https://winfuture.de/",
        parser=WinfutureParser,
        sources=[
            RSSFeed("https://static.winfuture.de/feeds/WinFuture-News-rss2.0.xml", languages={"de"}),
            NewsMap("https://winfuture.de/sitemap-latest-news.xml.gz", languages={"de"}),
            Sitemap(
                "https://winfuture.de/sitemap.xml",
                sitemap_filter=inverse(regex_filter("sitemap-news")),
                languages={"de"},
            ),
        ],
        url_filter=regex_filter("https:////winfuture/.de//news*"),
    )

    JungeWelt = Publisher(
        name="Junge Welt",
        domain="https://www.jungewelt.de/",
        parser=JungeWeltParser,
        sources=[
            RSSFeed("https://www.jungewelt.de/feeds/newsticker.rss", languages={"de"}),
        ],
    )

    Tagesspiegel = Publisher(
        name="Tagesspiegel",
        domain="https://www.tagesspiegel.de/",
        parser=TagesspiegelParser,
        sources=[
            NewsMap("https://www.tagesspiegel.de/news.xml", languages={"de"}),
        ]
        + [
            Sitemap(f"https://www.tagesspiegel.de/contentexport/static/sitemap-index_{date.year}.xml", languages={"de"})
            for date in reversed(list(rrule(YEARLY, dtstart=datetime(1996, 1, 1), until=datetime.today())))
        ],
    )

    EuronewsDE = Publisher(
        name="Euronews (DE)",
        domain="https://de.euronews.com/",
        parser=EuronewsParser,
        sources=[
            Sitemap("https://de.euronews.com/sitemaps/de/articles.xml", languages={"de"}),
            NewsMap("https://de.euronews.com/sitemaps/de/latest-news.xml", languages={"de"}),
        ],
    )

    Hessenschau = Publisher(
        name="Hessenschau",
        domain="https://www.hessenschau.de/",
        parser=HessenschauParser,
        sources=[
            RSSFeed("https://www.hessenschau.de/index.rss", languages={"de"}),
            Sitemap("https://www.hessenschau.de/indexsitemap.nc.xml", languages={"de"}),
            Sitemap("https://www.hessenschau.de/sitemap.nc.xml", languages={"de"}),
        ],
    )

    WDR = Publisher(
        name="Westdeutscher Rundfunk",
        domain="https://www1.wdr.de/",
        parser=WDRParser,
        sources=[RSSFeed("https://www1.wdr.de/uebersicht-100.feed", languages={"de"})],
    )

    BR = Publisher(
        name="Bayerischer Rundfunk (BR)",
        domain="https://www.br.de/",
        parser=BRParser,
        sources=[
            Sitemap("https://www.br.de/sitemapIndex.xml", languages={"de"}),
            NewsMap("https://www.br.de/nachrichten/sitemaps/news.xml", languages={"de"}),
        ],
    )

    ZDF = Publisher(
        name="ZDF",
        domain="https://www.zdf.de/",
        parser=ZDFParser,
        sources=[
            Sitemap("https://www.zdf.de/sitemap.xml", reverse=True, languages={"de"}),
            NewsMap("https://www.zdf.de/news-sitemap.xml", languages={"de"}),
            RSSFeed("https://www.zdf.de/rss/zdf/nachrichten", languages={"de"}),
        ],
    )

    MotorSportMagazin = Publisher(
        name="MotorSport Magazin",
        domain="https://www.motorsport-magazin.com/",
        parser=MotorSportMagazinParser,
        sources=[
            RSSFeed("https://www.motorsport-magazin.com/rss/alle-rennserien.xml", languages={"de"}),
            Sitemap("https://www.motorsport-magazin.com/sitemap.xml", languages={"de"}),
        ],
    )

    Postillon = Publisher(
        name="Postillon",
        domain="https://www.der-postillon.com/",
        parser=PostillonParser,
        sources=[
            RSSFeed("https://follow.it/der-postillon-abo", languages={"de"}),
            Sitemap("https://www.der-postillon.com/sitemap.xml", languages={"de"}),
        ],
    )

    Kicker = Publisher(
        name="Kicker",
        domain="https://www.kicker.de/",
        parser=KickerParser,
        sources=[
            RSSFeed("https://newsfeed.kicker.de/news/aktuell", languages={"de"}),
            Sitemap(
                "https://leserservice.kicker.de/sitemap_0.xml",
                sitemap_filter=regex_filter("leserservice.kicker.de"),
                languages={"de"},
            ),
            NewsMap("https://newsfeed.kicker.de/googlesitemapnews.xml", languages={"de"}),
        ],
        url_filter=regex_filter("/slideshow|/video"),
    )

    Krautreporter = Publisher(
        name="Krautreporter",
        domain="https://krautreporter.de/",
        parser=KrautreporterParser,
        sources=[
            # NOTE: robots.txt mentions that it reserves the right of use for text & data mining (§ 44 b UrhG),
            # but this is not in machine readable format, which is required by law for it to be effective.
            # NOTE: Unfortunately, both sitemap.xml and news.xml are identical.
            Sitemap("https://krautreporter.de/sitemap.xml", reverse=True, languages={"de"}),
            # NewsMap("https://krautreporter.de/news.xml", languages={"de"}),
            RSSFeed("https://krautreporter.de/feeds.rss", languages={"de"}),
        ],
        url_filter=regex_filter(r"/(pages|archiv|serien|thema|zusammenhaenge)/"),
    )

    FrankfurterRundschau = Publisher(
        name="Frankfurter Rundschau",
        domain="https://www.fr.de",
        parser=FrankfurterRundschauParser,
        sources=[
            RSSFeed("https://fr.de/rssfeed.rdf", languages={"de"}),
            Sitemap("https://www.fr.de/sitemap-index.xml", languages={"de"}),
            NewsMap("https://www.fr.de/news.xml", languages={"de"}),
        ],
    )

    BoersenZeitung = Publisher(
        name="Börsen-Zeitung",
        domain="https://www.boersen-zeitung.de",
        parser=BoersenZeitungParser,
        sources=[
            NewsMap("https://www.boersen-zeitung.de/sitemap/news.xml.gz", languages={"de"}),
            Sitemap(
                "https://www.boersen-zeitung.de/sitemap/index.xml.gz",
                sitemap_filter=regex_filter("/sitemap-0.xml.gz"),
                languages={"de"},
            ),
        ],
    )

    VogueDE = Publisher(
        name="Vogue",
        domain="https://www.vogue.de/",
        parser=VogueDEParser,
        sources=[
            RSSFeed("https://www.vogue.de/feed/rss", languages={"de"}),
            NewsMap("https://www.vogue.de/feed/sitemap-news/sitemap-google-news", languages={"de"}),
            Sitemap("https://www.vogue.de/sitemap.xml", languages={"de"}),
        ],
    )

    MitteldeutscheZeitung = Publisher(
        name="Mitteldeutsche Zeitung",
        domain="https://www.mz.de/",
        parser=MitteldeutscheZeitungParser,
        sources=[
            Sitemap("https://www.mz.de/sitemaps/sitemap-ressort-index.xml", languages={"de"}),
            NewsMap("https://www.mz.de/sitemaps/newssitemap-index.xml", languages={"de"}),
        ],
    )

    FreiePresse = Publisher(
        name="FreiePresse",
        domain="https://www.freiepresse.de/",
        parser=FreiePresseParser,
        sources=[
            RSSFeed("https://www.freiepresse.de/rss/rss_chemnitz.php", languages={"de"}),
            RSSFeed("https://www.freiepresse.de/rss/rss_erzgebirge.php", languages={"de"}),
            RSSFeed("https://www.freiepresse.de/rss/rss_mittelsachsen.php", languages={"de"}),
            RSSFeed("https://www.freiepresse.de/rss/rss_vogtland.php", languages={"de"}),
            RSSFeed("https://www.freiepresse.de/rss/rss_zwickau.php", languages={"de"}),
            RSSFeed("https://www.freiepresse.de/rss/rss_politik.php", languages={"de"}),
            RSSFeed("https://www.freiepresse.de/rss/rss_wirtschaft.php", languages={"de"}),
            RSSFeed("https://www.freiepresse.de/rss/rss_kultur.php", languages={"de"}),
            RSSFeed("https://www.freiepresse.de/rss/rss_sport.php", languages={"de"}),
            RSSFeed("https://www.freiepresse.de/rss/rss_sachsen.php", languages={"de"}),
            RSSFeed("https://www.freiepresse.de/rss/rss_regional.php", languages={"de"}),
            Sitemap("https://www.freiepresse.de/sitemaps/articles_last2years.xml", reverse=True, languages={"de"}),
        ],
    )

    RuhrNachrichten = Publisher(
        name="Ruhr Nachrichten",
        domain="https://www.ruhrnachrichten.de/",
        parser=RuhrNachrichtenParser,
        sources=[
            RSSFeed("https://www.ruhrnachrichten.de/service/feed/", languages={"de"}),
            NewsMap("https://www.ruhrnachrichten.de/news-sitemap.xml", languages={"de"}),
            Sitemap(
                "https://www.ruhrnachrichten.de/sitemap_index.xml",
                reverse=True,
                sitemap_filter=inverse(regex_filter("post-sitemap")),
                languages={"de"},
            ),
        ],
    )

    Gamestar = Publisher(
        name="Gamestar",
        domain="https://www.gamestar.de/",
        parser=GamestarParser,
        sources=[
            NewsMap("https://www.gamestar.de/sitemapnews.xml", languages={"de"}),
            Sitemap("https://www.gamestar.de/artikel_archiv_index.xml", languages={"de"}),
        ],
    )
