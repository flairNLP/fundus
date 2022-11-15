from src.library.collection.base_objects import PublisherEnum, PublisherSpec
from .die_welt_parser import DieWeltParser
from .mdr_parser import MDRParser


# noinspection PyPep8Naming
class DE_DE(PublisherEnum):
    DieWelt = PublisherSpec(domain='https://www.welt.de/', rss_feeds=['https://www.welt.de/feeds/latest.rss'],
                            parser=DieWeltParser)
    MDR = PublisherSpec(domain='https://www.mdr.de/', rss_feeds=['https://www.mdr.de/nachrichten/index-rss.xml'],
                        sitemaps=['https://www.mdr.de/news-sitemap.xml'], parser=MDRParser)
