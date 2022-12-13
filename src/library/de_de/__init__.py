from src.library.collection.base_objects import PublisherEnum, PublisherSpec
from .bz_parser import BZParser
from .die_welt_parser import DieWeltParser
from .dw_parser import DWParser
from .focus_parser import FocusParser
from .mdr_parser import MDRParser


# noinspection PyPep8Naming
class DE_DE(PublisherEnum):
    DieWelt = PublisherSpec(domain='https://www.welt.de/', rss_feeds=['https://www.welt.de/feeds/latest.rss'],
                            parser=DieWeltParser)
    MDR = PublisherSpec(domain='https://www.mdr.de/', rss_feeds=['https://www.mdr.de/nachrichten/index-rss.xml'],
                        sitemaps=['https://www.mdr.de/news-sitemap.xml'], parser=MDRParser)

    DW = PublisherSpec(domain='https://www.dw.com/', sitemaps=["https://www.dw.com/de/sitemap-news.xml"],
                       parser=DWParser)
    Focus = PublisherSpec(domain='https://www.focus.de/', rss_feeds=['https://rss.focus.de/fol/XML/rss_folnews.xml'], parser=FocusParser)

