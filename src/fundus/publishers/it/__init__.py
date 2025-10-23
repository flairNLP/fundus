from datetime import datetime, timedelta

from dateutil.rrule import MONTHLY, rrule

from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.it.corriere_della_sera import CorriereDellaSeraParser
from fundus.publishers.it.il_giornale import IlGiornaleParser
from fundus.publishers.it.la_repubblica import LaRepubblicaParser
from fundus.publishers.it.tageszeitung import TageszeitungParser
from fundus.scraping.filter import regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap


class IT(metaclass=PublisherGroup):
    default_language = "it"

    LaRepubblica = Publisher(
        name="La Repubblica",
        domain="https://www.repubblica.it",
        parser=LaRepubblicaParser,
        sources=[
            RSSFeed("https://www.repubblica.it/rss/homepage/rss2.0.xml"),
        ]
        + [
            Sitemap(f"https://www.repubblica.it/sitemap-{date.strftime('%Y-%m')}.xml")
            for date in reversed(
                list(rrule(MONTHLY, dtstart=datetime(2020, 1, 1), until=datetime.now() + timedelta(days=30)))
            )
        ],
    )

    CorriereDellaSera = Publisher(
        name="Corriere della Sera",
        domain="https://www.corriere.it",
        parser=CorriereDellaSeraParser,
        sources=[
            # Main RSS feeds
            RSSFeed("https://www.corriere.it/rss/homepage.xml"),
            RSSFeed("https://www.corriere.it/rss/ultimora.xml"),  ## Current empty but could be in use
            RSSFeed("https://www.corriere.it/dynamic-feed/rss/section/Dataroom.xml"),
            RSSFeed("https://www.corriere.it/dynamic-feed/rss/section/lettere-al-direttore.xml"),
            RSSFeed("https://www.corriere.it/dynamic-feed/rss/section/lo-dico-al-corriere.xml"),
            RSSFeed("https://www.corriere.it/dynamic-feed/rss/section/frammenti-di-ferruccio-de-bortoli.xml"),
            # Main sitemaps
            Sitemap("https://www.corriere.it/rss/sitemap_v2.xml"),
            # Dynamic sitemaps - Last 100 articles
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Economia.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Salute.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Scienze.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Interni.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Esteri.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Sport.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Politica.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Salute__Figli__e__Genitori.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Salute__Sportello__Cancro.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Elezioni.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Tecnologia.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Offerte__recensioni.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Lotterie.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Spettacoli.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Scuola.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Animali.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Opinioni.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Caffe-gramellini.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Ultimo-banco.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Letti-da-rifarei.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Piccole-dosi.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/L-angolo.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Padiglione-italia.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Facce-nuove.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Ritorno-in-solferino.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Oriente-occidente.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Sette.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Moda.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/BuoneNotizie.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/lettere__al__direttore.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/lo__dico__al__corriere.xml"),
            Sitemap("https://www.corriere.it/dynamic-sitemap/sitemap-last-100/Frammenti-ferruccio-de-bortoli.xml"),
            # Section sitemaps
            Sitemap("https://www.corriere.it/rss/sitemap/Motori.xml"),
            Sitemap("https://www.corriere.it/rss/sitemap/Cultura.xml"),
            Sitemap("https://www.corriere.it/rss/sitemap/lettere-al-direttore.xml"),
            Sitemap("https://www.corriere.it/rss/sitemap/lo-dico-al-corriere.xml"),
            Sitemap("https://www.corriere.it/rss/sitemap/Cook-Last.xml"),
        ],
    )

    IlGiornale = Publisher(
        name="Il Giornale",
        domain="https://www.ilgiornale.it",
        parser=IlGiornaleParser,
        sources=[
            # Main RSS feed (removed the one returning 404)
            RSSFeed("https://www.ilgiornale.it/feed.xml"),
            # Main sitemaps - excluding video and image sitemaps
            NewsMap("https://www.ilgiornale.it/sitemap/google-news.xml"),
            Sitemap(
                "https://www.ilgiornale.it/sitemap/indice.xml",
                sitemap_filter=regex_filter(r"\*/video/|\*/image/"),
            ),
        ],
    )

    Tageszeitung = Publisher(
        name="Die Neue Südtiroler Tageszeitung",
        domain="https://www.tageszeitung.it",
        parser=TageszeitungParser,
        sources=[
            Sitemap(
                "https://www.tageszeitung.it/sitemap.xml",
                sitemap_filter=regex_filter(r"page|misc|\/sitemap\.xml"),
                languages={"de"},
            ),
        ],
    )
