from src.library.collection.base_objects import PublisherEnum, PublisherSpec
from .die_welt_parser import DieWeltParser
from .faz_parser import FAZParser
from .focus_parser import FocusParser
from .mdr_parser import MDRParser
from .merkur_parser import MerkurParser
from .sz_parser import SZParser
from .tagesschau_parser import TagesschauParser


# noinspection PyPep8Naming
class DE_DE(PublisherEnum):
    DieWelt = PublisherSpec(domain='https://www.welt.de/',
                            rss_feeds=['https://www.welt.de/feeds/latest.rss'],
                            parser=DieWeltParser)

    MDR = PublisherSpec(domain='https://www.mdr.de/',
                        rss_feeds=['https://www.mdr.de/nachrichten/index-rss.xml'],
                        parser=MDRParser)

    FAZ = PublisherSpec(domain='https://www.faz.net/',
                        rss_feeds=['https://www.faz.net/rss/aktuell',
                                   'https://www.faz.net/rss/aktuell/politik',
                                   'https://www.faz.net/rss/aktuell/sport',
                                   'https://www.faz.net/rss/aktuell/wirtschaft/',
                                   'https://www.faz.net/rss/aktuell/gesellschaft/'],
                        parser=FAZParser)

    Focus = PublisherSpec(domain='https://www.focus.de/',
                          rss_feeds=['https://rss.focus.de/fol/XML/rss_folnews.xml'],
                          parser=FocusParser)

    Merkur = PublisherSpec(domain='https://www.merkur.de/',
                           rss_feeds=['https://www.merkur.de/welt/rssfeed.rdf'],
                           parser=MerkurParser)

    SZ = PublisherSpec(domain='https://www.sueddeutsche.de/',
                       rss_feeds=["https://rss.sueddeutsche.de/app/service/rss/alles/index.rss?output=rss"],
                       parser=SZParser)

    Tagesschau = PublisherSpec(domain='https://www.tagesschau.de/',
                               rss_feeds=['https://www.tagesschau.de/xml/rss2/'],
                               parser=TagesschauParser)
