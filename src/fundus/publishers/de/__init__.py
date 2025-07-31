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
from .business_insider_de import BusinessInsiderDEParser
from .die_welt import DieWeltParser
from .die_zeit import DieZeitParser
from .dw import DWParser
from .faz import FAZParser
from .focus import FocusParser
from .frankfurter_rundschau import FrankfurterRundschauParser
from .freiepresse import FreiePresseParser
from .funke import FunkeParser
from .gamestar import GamestarParser
from .golem import GolemParser
from .heise import HeiseParser
from .hessenschau import HessenschauParser
from .junge_welt import JungeWeltParser
from .kicker import KickerParser
from .krautreporter import KrautreporterParser
from .mdr import MDRParser
from .merkur import MerkurParser
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
    default_language = "de"

    SportSchau = Publisher(
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

    NetzpolitikOrg = Publisher(
        name="netzpolitik.org",
        domain="https://netzpolitik.org/",
        parser=NetzpolitikOrgParser,
        sources=[
            Sitemap(
                "https://netzpolitik.org/sitemap.xml",
                sitemap_filter=inverse(regex_filter("sitemap-posttype-post")),
            ),
            RSSFeed("https://netzpolitik.org/feed/"),
        ],
    )

    BerlinerMorgenpost = Publisher(
        name="Berliner Morgenpost",
        domain="https://www.morgenpost.de/",
        parser=FunkeParser,
        sources=[NewsMap("https://www.morgenpost.de/sitemaps/news.xml")]
        + [
            Sitemap(
                f"https://www.morgenpost.de/sitemaps/archive/sitemap-{d.year}-{str(d.month).zfill(2)}-p00.xml.gz",
            )
            for d in reversed(list(rrule(MONTHLY, dtstart=datetime(2003, 2, 1), until=datetime.now())))
        ],
    )

    HamburgerAbendblatt = Publisher(
        name="Hamburger Abendblatt",
        domain="https://www.abendblatt.de/",
        parser=FunkeParser,
        sources=[
            RSSFeed("https://www.abendblatt.de/rss"),
            NewsMap("https://www.abendblatt.de/sitemaps/news.xml"),
        ]
        + [
            Sitemap(
                f"https://www.abendblatt.de/sitemaps/archive/sitemap-{d.year}-{str(d.month).zfill(2)}-p00.xml.gz",
            )
            for d in reversed(list(rrule(MONTHLY, dtstart=datetime(2000, 4, 1), until=datetime.today())))
        ],
    )

    DieWelt = Publisher(
        name="Die Welt",
        domain="https://www.welt.de/",
        parser=DieWeltParser,
        sources=[
            RSSFeed("https://www.welt.de/feeds/latest.rss"),
            Sitemap("https://www.welt.de/sitemaps/sitemap/sitemap.xml"),
            NewsMap("https://www.welt.de/sitemaps/newssitemap/newssitemap.xml"),
        ],
        url_filter=regex_filter("/Anlegertipps-|/videos?[0-9]{2}|/mediathek/"),
    )

    MDR = Publisher(
        name="Mitteldeutscher Rundfunk (MDR)",
        domain="https://www.mdr.de/",
        parser=MDRParser,
        sources=[
            RSSFeed("https://www.mdr.de/nachrichten/index-rss.xml"),
            Sitemap("https://www.mdr.de/sitemap-index-100.xml"),
            NewsMap("https://www.mdr.de/news-sitemap.xml"),
        ],
    )

    FAZ = Publisher(
        name="Frankfurter Allgemeine Zeitung",
        domain="https://www.faz.net/",
        parser=FAZParser,
        sources=[
            RSSFeed("https://www.faz.net/rss/aktuell"),
            RSSFeed("https://www.faz.net/rss/aktuell/politik"),
            RSSFeed("https://www.faz.net/rss/aktuell/sport"),
            RSSFeed("https://www.faz.net/rss/aktuell/wirtschaft/"),
            RSSFeed("https://www.faz.net/rss/aktuell/gesellschaft/"),
            Sitemap("https://www.faz.net/sitemap-index.xml", sitemap_filter=inverse(regex_filter("-artikel-"))),
            NewsMap("https://www.faz.net/sitemap-news.xml"),
        ],
    )

    Focus = Publisher(
        name="Focus Online",
        domain="https://www.focus.de/",
        parser=FocusParser,
        sources=[
            NewsMap("https://www.focus.de/sitemap_news_ressorts.xml"),
        ],
        request_header={"user-agent": "Fundus"},
    )

    Merkur = Publisher(
        name="Münchner Merkur",
        domain="https://www.merkur.de/",
        parser=MerkurParser,
        sources=[
            RSSFeed("https://www.merkur.de/welt/rssfeed.rdf"),
            Sitemap("https://www.merkur.de/sitemap-index.xml"),
            NewsMap("https://www.merkur.de/news.xml"),
        ],
    )

    SZ = Publisher(
        name="Süddeutsche Zeitung",
        domain="https://www.sueddeutsche.de/",
        parser=SZParser,
        sources=[RSSFeed("https://rss.sueddeutsche.de/alles")],
    )

    SpiegelOnline = Publisher(
        name="Spiegel Online",
        domain="https://www.spiegel.de/",
        parser=SPONParser,
        sources=[
            RSSFeed("https://www.spiegel.de/schlagzeilen/index.rss"),
            Sitemap("https://www.spiegel.de/sitemap.xml"),
            NewsMap("https://www.spiegel.de/sitemaps/news-de.xml"),
        ],
        request_header={"User-Agent": "Googlebot"},
    )

    DieZeit = Publisher(
        name="Die Zeit",
        domain="https://www.zeit.de/",
        parser=DieZeitParser,
        sources=[
            RSSFeed("https://newsfeed.zeit.de/news/index"),
            Sitemap("https://www.zeit.de/gsitemaps/index.xml", reverse=True),
            NewsMap(
                f"https://www.zeit.de/gsitemaps/index.xml?date={datetime.now().strftime('%Y-%m-%d')}&unit=days&period=1",
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
            RSSFeed("https://www.berliner-zeitung.de/feed.xml"),
            Sitemap("https://www.berliner-zeitung.de/sitemap.xml"),
            NewsMap("https://www.berliner-zeitung.de/news-sitemap.xml"),
        ],
        url_filter=regex_filter("/news/"),
    )

    Tagesschau = Publisher(
        name="Tagesschau",
        domain="https://www.tagesschau.de/",
        parser=TagesschauParser,
        sources=[RSSFeed("https://www.tagesschau.de/xml/rss2/")],
    )

    DW = Publisher(
        name="Deutsche Welle",
        domain="https://www.dw.com/",
        parser=DWParser,
        sources=[
            RSSFeed("https://rss.dw.com/xml/rss-de-all"),
            Sitemap("https://www.dw.com/de/article-sitemap.xml"),
            NewsMap("https://www.dw.com/de/news-sitemap.xml"),
            RSSFeed("https://rss.dw.com/xml/rss-en-all", languages={"en"}),
            Sitemap("https://www.dw.com/en/article-sitemap.xml", languages={"en"}),
            NewsMap("https://www.dw.com/en/news-sitemap.xml", languages={"en"}),
        ],
    )
    Stern = Publisher(
        name="Stern",
        domain="https://www.stern.de/",
        parser=SternParser,
        sources=[RSSFeed("https://www.stern.de/feed/standard/alle-nachrichten/")],
    )

    NTV = Publisher(
        name="N-Tv",
        domain="https://www.n-tv.de/",
        parser=NTVParser,
        sources=[
            NewsMap("https://www.n-tv.de/news.xml"),
            Sitemap("https://www.n-tv.de/sitemap.xml", sitemap_filter=regex_filter("sitemap-sections")),
        ],
    )

    NDR = Publisher(
        name="Norddeutscher Rundfunk (NDR)",
        domain="https://www.ndr.de/",
        parser=NDRParser,
        sources=[
            NewsMap("https://www.ndr.de/news-102~news.xml"),
            Sitemap("https://www.ndr.de/index~sitemap_f-sitemap--ndr--info--100.xml"),
            Sitemap("https://www.ndr.de/index~sitemap_f-sitemap--ndr--niedersachsen--100.xml"),
            Sitemap("https://www.ndr.de/index~sitemap_f-sitemap--ndr--schleswig--holstein--100.xml"),
            Sitemap("https://www.ndr.de/index~sitemap_f-sitemap--ndr--mecklenburg--vorpommern--100.xml"),
            Sitemap("https://www.ndr.de/index~sitemap_f-sitemap--ndr--hamburg--100.xml"),
            Sitemap("https://www.ndr.de/index~sitemap_f-sitemap--ndr--sport--100.xml"),
            Sitemap("https://www.ndr.de/index~sitemap_f-sitemap--ndr--kultur--100.xml"),
            Sitemap("https://www.ndr.de/index~sitemap_f-sitemap--ndr--geschichte--100.xml"),
        ],
        url_filter=regex_filter("podcast[0-9]{4}|/index.html"),
    )

    Taz = Publisher(
        name="Die Tageszeitung (taz)",
        domain="https://taz.de/",
        parser=TazParser,
        sources=[
            NewsMap("https://taz.de/sitemap-google-news.xml"),
            Sitemap("https://taz.de/sitemap-index.xml"),
        ],
    )

    Heise = Publisher(
        name="Heise",
        domain="https://www.heise.de",
        sources=[
            RSSFeed("https://www.heise.de/rss/heise.rdf"),
            Sitemap(
                "https://www.heise.de/sitemapindex.xml",
                sitemap_filter=inverse(regex_filter("/news/")),
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
            RSSFeed("https://www.bild.de/feed/alles.xml"),
            NewsMap("https://www.bild.de/sitemap-news.xml"),
            Sitemap("https://www.bild.de/sitemap-index.xml"),
        ],
    )

    WAZ = Publisher(
        name="Westdeutsche Allgemeine Zeitung (WAZ)",
        domain="https://www.waz.de/",
        parser=WAZParser,
        sources=[NewsMap("https://www.waz.de/sitemaps/news.xml")],
    )

    BSZ = Publisher(
        name="Braunschweiger Zeitung",
        domain="https://www.braunschweiger-zeitung.de/",
        parser=FunkeParser,
        sources=[
            RSSFeed("https://www.braunschweiger-zeitung.de/rss"),
            NewsMap("https://www.braunschweiger-zeitung.de/sitemaps/news.xml"),
        ]
        + [
            Sitemap(
                f"https://www.braunschweiger-zeitung.de/sitemaps/archive/sitemap-{d.year}-{str(d.month).zfill(2)}-p00.xml.gz",
            )
            for d in list(rrule(MONTHLY, dtstart=datetime(2005, 12, 1), until=datetime.now()))
        ],
    )

    BusinessInsiderDE = Publisher(
        name="Business Insider DE",
        domain="https://www.businessinsider.de/",
        parser=BusinessInsiderDEParser,
        sources=[
            RSSFeed("https://www.businessinsider.de/feed/businessinsider-alle-artikel"),
            NewsMap("https://www.businessinsider.de/news-sitemap.xml"),
            Sitemap(
                "https://www.businessinsider.de/sitemap_index.xml",
                sitemap_filter=inverse(regex_filter("post-sitemap")),
                reverse=True,
            ),
        ],
    )

    RheinischePost = Publisher(
        name="Rheinische Post",
        domain="https://rp-online.de/",
        parser=RheinischePostParser,
        sources=[
            RSSFeed("https://rp-online.de/feed.rss"),
            NewsMap("https://rp-online.de/sitemap-news.xml"),
            Sitemap("https://rp-online.de/sitemap.xml"),
        ],
    )

    Golem = Publisher(
        name="Golem",
        domain="https://www.golem.de/",
        sources=[
            RSSFeed("https://www.golem.de/rss"),
            NewsMap("https://www.golem.de/news/gsitemap-2404.xml"),
            Sitemap("https://www.golem.de/gsiteindex.xml"),
        ],
        request_header={"User-Agent": "Googlebot"},
        parser=GolemParser,
    )

    WinFuture = Publisher(
        name="WinFuture",
        domain="https://winfuture.de/",
        parser=WinfutureParser,
        sources=[
            RSSFeed("https://static.winfuture.de/feeds/WinFuture-News-rss2.0.xml"),
            NewsMap("https://winfuture.de/sitemap-latest-news.xml.gz"),
            Sitemap(
                "https://winfuture.de/sitemap.xml",
                sitemap_filter=inverse(regex_filter("sitemap-news")),
            ),
        ],
        url_filter=regex_filter("https:////winfuture/.de//news*"),
    )

    JungeWelt = Publisher(
        name="Junge Welt",
        domain="https://www.jungewelt.de/",
        parser=JungeWeltParser,
        sources=[
            RSSFeed("https://www.jungewelt.de/feeds/newsticker.rss"),
        ],
    )

    Tagesspiegel = Publisher(
        name="Tagesspiegel",
        domain="https://www.tagesspiegel.de/",
        parser=TagesspiegelParser,
        sources=[
            NewsMap("https://www.tagesspiegel.de/news.xml"),
        ]
        + [
            Sitemap(f"https://www.tagesspiegel.de/contentexport/static/sitemap-index_{date.year}.xml")
            for date in reversed(list(rrule(YEARLY, dtstart=datetime(1996, 1, 1), until=datetime.today())))
        ],
    )

    EuronewsDE = Publisher(
        name="Euronews (DE)",
        domain="https://de.euronews.com/",
        parser=EuronewsParser,
        sources=[
            Sitemap("https://de.euronews.com/sitemaps/de/articles.xml"),
            NewsMap("https://de.euronews.com/sitemaps/de/latest-news.xml"),
        ],
        url_filter=regex_filter("/video/"),
    )

    Hessenschau = Publisher(
        name="Hessenschau",
        domain="https://www.hessenschau.de/",
        parser=HessenschauParser,
        sources=[
            RSSFeed("https://www.hessenschau.de/index.rss"),
            Sitemap("https://www.hessenschau.de/indexsitemap.nc.xml"),
            Sitemap("https://www.hessenschau.de/sitemap.nc.xml"),
        ],
    )

    WDR = Publisher(
        name="Westdeutscher Rundfunk",
        domain="https://www1.wdr.de/",
        parser=WDRParser,
        sources=[RSSFeed("https://www1.wdr.de/uebersicht-100.feed")],
        url_filter=inverse(regex_filter("wdr.de/(?!mediathek/)")),
    )

    BR = Publisher(
        name="Bayerischer Rundfunk (BR)",
        domain="https://www.br.de/",
        parser=BRParser,
        sources=[
            Sitemap("https://www.br.de/sitemapIndex.xml"),
            NewsMap("https://www.br.de/nachrichten/sitemaps/news.xml"),
        ],
    )

    ZDF = Publisher(
        name="ZDF",
        domain="https://www.zdf.de/",
        parser=ZDFParser,
        sources=[
            Sitemap("https://www.zdf.de/sitemap.xml", reverse=True),
            NewsMap("https://www.zdf.de/news-sitemap.xml"),
            RSSFeed("https://www.zdf.de/rss/zdf/nachrichten"),
        ],
    )

    MotorSportMagazin = Publisher(
        name="MotorSport Magazin",
        domain="https://www.motorsport-magazin.com/",
        parser=MotorSportMagazinParser,
        sources=[
            RSSFeed("https://www.motorsport-magazin.com/rss/alle-rennserien.xml"),
            Sitemap("https://www.motorsport-magazin.com/sitemap.xml"),
        ],
    )

    Postillon = Publisher(
        name="Postillon",
        domain="https://www.der-postillon.com/",
        parser=PostillonParser,
        sources=[
            RSSFeed("https://follow.it/der-postillon-abo"),
            Sitemap("https://www.der-postillon.com/sitemap.xml"),
        ],
        url_filter=regex_filter("https://follow.it/"),
    )

    Kicker = Publisher(
        name="Kicker",
        domain="https://www.kicker.de/",
        parser=KickerParser,
        sources=[
            RSSFeed("https://newsfeed.kicker.de/news/aktuell"),
            Sitemap(
                "https://leserservice.kicker.de/sitemap_0.xml",
                sitemap_filter=regex_filter("leserservice.kicker.de"),
            ),
            NewsMap("https://newsfeed.kicker.de/googlesitemapnews.xml"),
        ],
        url_filter=regex_filter("/slideshow|/video|heute-live|live-konferenz|/bilder|/ticker"),
    )

    Krautreporter = Publisher(
        name="Krautreporter",
        domain="https://krautreporter.de/",
        parser=KrautreporterParser,
        sources=[
            # NOTE: robots.txt mentions that it reserves the right of use for text & data mining (§ 44 b UrhG),
            # but this is not in machine readable format, which is required by law for it to be effective.
            # NOTE: Unfortunately, both sitemap.xml and news.xml are identical.
            Sitemap("https://krautreporter.de/sitemap.xml", reverse=True),
            # NewsMap("https://krautreporter.de/news.xml"),
            RSSFeed("https://krautreporter.de/feeds.rss"),
        ],
        url_filter=regex_filter(r"/(pages|archiv|serien|thema|zusammenhaenge)/"),
    )

    FrankfurterRundschau = Publisher(
        name="Frankfurter Rundschau",
        domain="https://www.fr.de",
        parser=FrankfurterRundschauParser,
        sources=[
            RSSFeed("https://fr.de/rssfeed.rdf"),
            Sitemap("https://www.fr.de/sitemap-index.xml"),
            NewsMap("https://www.fr.de/news.xml"),
        ],
    )

    BoersenZeitung = Publisher(
        name="Börsen-Zeitung",
        domain="https://www.boersen-zeitung.de",
        parser=BoersenZeitungParser,
        sources=[
            NewsMap("https://www.boersen-zeitung.de/sitemap/news.xml.gz"),
            Sitemap(
                "https://www.boersen-zeitung.de/sitemap/index.xml.gz",
                sitemap_filter=regex_filter("/sitemap-0.xml.gz"),
            ),
        ],
    )

    VogueDE = Publisher(
        name="Vogue",
        domain="https://www.vogue.de/",
        parser=VogueDEParser,
        sources=[
            RSSFeed("https://www.vogue.de/feed/rss"),
            NewsMap("https://www.vogue.de/feed/sitemap-news/sitemap-google-news"),
            Sitemap("https://www.vogue.de/sitemap.xml"),
        ],
    )

    MitteldeutscheZeitung = Publisher(
        name="Mitteldeutsche Zeitung",
        domain="https://www.mz.de/",
        parser=MitteldeutscheZeitungParser,
        sources=[
            Sitemap("https://www.mz.de/sitemaps/sitemap-ressort-index.xml"),
            NewsMap("https://www.mz.de/sitemaps/newssitemap-index.xml"),
        ],
    )

    FreiePresse = Publisher(
        name="FreiePresse",
        domain="https://www.freiepresse.de/",
        parser=FreiePresseParser,
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
    )

    RuhrNachrichten = Publisher(
        name="Ruhr Nachrichten",
        domain="https://www.ruhrnachrichten.de/",
        parser=RuhrNachrichtenParser,
        sources=[
            RSSFeed("https://www.ruhrnachrichten.de/service/feed/"),
            NewsMap("https://www.ruhrnachrichten.de/news-sitemap.xml"),
            Sitemap(
                "https://www.ruhrnachrichten.de/sitemap_index.xml",
                reverse=True,
                sitemap_filter=inverse(regex_filter("post-sitemap")),
            ),
        ],
    )

    Gamestar = Publisher(
        name="Gamestar",
        domain="https://www.gamestar.de/",
        parser=GamestarParser,
        sources=[
            NewsMap("https://www.gamestar.de/sitemapnews.xml"),
            Sitemap("https://www.gamestar.de/artikel_archiv_index.xml"),
        ],
    )
