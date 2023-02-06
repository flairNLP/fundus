from src.library.collection.base_objects import PublisherEnum, PublisherSpec
from .die_welt_parser import DieWeltParser
from .faz_parser import FAZParser
from .focus_parser import FocusParser
from .mdr_parser import MDRParser
from .merkur_parser import MerkurParser
from .orf_parser import OrfParser


# noinspection PyPep8Naming
class DE_DE(PublisherEnum):
    DieWelt = PublisherSpec(domain='https://www.welt.de/',
                            rss_feeds=['https://www.welt.de/feeds/latest.rss'],
                            parser=DieWeltParser)

    MDR = PublisherSpec(domain='https://www.mdr.de/',
                        rss_feeds=['https://www.mdr.de/nachrichten/index-rss.xml'],
                        sitemaps=['https://www.mdr.de/news-sitemap.xml'],
                        parser=MDRParser)

    FAZ = PublisherSpec(domain='https://www.faz.net/',
                        rss_feeds=['https://www.faz.net/rss/aktuell', 'https://www.faz.net/rss/aktuell/politik',
                                   'https://www.faz.net/rss/aktuell/sport',
                                   'https://www.faz.net/rss/aktuell/wirtschaft/',
                                   'https://www.faz.net/rss/aktuell/gesellschaft/'],
                        parser=FAZParser)

    Focus = PublisherSpec(domain='https://www.focus.de/',
                          rss_feeds=['https://rss.focus.de/fol/XML/rss_folnews.xml'],
                          sitemaps=[],
                          parser=FocusParser)

    Merkur = PublisherSpec(domain='https://www.merkur.de/',
                           rss_feeds=['https://www.merkur.de/welt/rssfeed.rdf'],
                           sitemaps=[],
                           parser=MerkurParser)

    ORF = PublisherSpec(domain='https://www.orf.at',
                        rss_feeds=["https://rss.orf.at/news.xml"],
                        sitemaps=[],
                        parser=OrfParser)
