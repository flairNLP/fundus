from datetime import datetime

from src.library.collection.base_objects import PublisherEnum, PublisherSpec

from .berliner_zeitung_parser import BerlinerZeitungParser
from .die_welt_parser import DieWeltParser
from .die_zeit_parser import DieZeitParser
from .dw_parser import DWParser
from .faz_parser import FAZParser
from .focus_parser import FocusParser
from .mdr_parser import MDRParser
from .merkur_parser import MerkurParser
from .spon_parser import SPONParser
from .stern_parser import SternParser
from .sz_parser import SZParser
from .tagesschau_parser import TagesschauParser
from .waz_parser import WAZParser


# noinspection PyPep8Naming
class DE(PublisherEnum):
    DieWelt = PublisherSpec(
        domain="https://www.welt.de/",
        rss_feeds=["https://www.welt.de/feeds/latest.rss"],
        sitemaps=["https://www.welt.de/sitemaps/sitemap/sitemap.xml"],
        news_map="https://www.welt.de/sitemaps/newssitemap/newssitemap.xml",
        parser=DieWeltParser,
    )

    MDR = PublisherSpec(
        domain="https://www.mdr.de/",
        rss_feeds=["https://www.mdr.de/nachrichten/index-rss.xml"],
        sitemaps=["https://www.mdr.de/sitemap-index-100.xml"],
        news_map="https://www.mdr.de/news-sitemap.xml",
        parser=MDRParser,
    )

    FAZ = PublisherSpec(
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
        domain="https://www.focus.de/",
        rss_feeds=["https://rss.focus.de/fol/XML/rss_folnews.xml"],
        parser=FocusParser,
    )

    Merkur = PublisherSpec(
        domain="https://www.merkur.de/",
        rss_feeds=["https://www.merkur.de/welt/rssfeed.rdf"],
        sitemaps=["https://www.merkur.de/sitemap-index.xml"],
        news_map="https://www.merkur.de/news.xml",
        parser=MerkurParser,
    )

    SZ = PublisherSpec(
        domain="https://www.sueddeutsche.de/",
        rss_feeds=["https://rss.sueddeutsche.de/alles"],
        parser=SZParser,
    )

    SpiegelOnline = PublisherSpec(
        domain="https://www.spiegel.de/",
        rss_feeds=["https://www.spiegel.de/schlagzeilen/index.rss"],
        sitemaps=["https://www.spiegel.de/sitemap.xml"],
        news_map="https://www.spiegel.de/sitemaps/news-de.xml",
        parser=SPONParser,
    )

    DieZeit = PublisherSpec(
        domain="https://www.sueddeutsche.de/",
        rss_feeds=["https://newsfeed.zeit.de/news/index"],
        sitemaps=["https://www.zeit.de/gsitemaps/index.xml"],
        news_map=f"https://www.zeit.de/gsitemaps/index.xml?date="
        f'{datetime.now().strftime("%Y-%m-%d")}&unit=days&period=1',
        parser=DieZeitParser,
    )

    BerlinerZeitung = PublisherSpec(
        domain="https://www.sueddeutsche.de/",
        rss_feeds=["https://www.berliner-zeitung.de/feed.xml"],
        sitemaps=["https://www.berliner-zeitung.de/sitemap.xml"],
        news_map="https://www.berliner-zeitung.de/news-sitemap.xml",
        parser=BerlinerZeitungParser,
    )

    Tagesschau = PublisherSpec(
        domain="https://www.tagesschau.de/",
        rss_feeds=["https://www.tagesschau.de/xml/rss2/"],
        parser=TagesschauParser,
    )

    DW = PublisherSpec(
        domain="https://www.dw.com/",
        rss_feeds=["https://rss.dw.com/xml/rss-de-all"],
        sitemaps=["https://www.dw.com/de/article-sitemap.xml"],
        news_map="https://www.dw.com/de/news-sitemap.xml",
        parser=DWParser,
    )
    Stern = PublisherSpec(
        domain="https://www.stern.de/",
        rss_feeds=["https://www.stern.de/feed/standard/alle-nachrichten/"],
        parser=SternParser,
    )

    WAZ = PublisherSpec(
        domain="https://www.waz.de/",
        news_map="https://www.waz.de/sitemaps/news.xml",
        parser=WAZParser,
    )
