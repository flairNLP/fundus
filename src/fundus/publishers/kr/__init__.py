from fundus.publishers.base_objects import PublisherGroup, Publisher
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap
from fundus.scraping.filter import regex_filter, inverse

#from .newsis import NewsisParser
from .mbn import MBNParser

class KR(metaclass=PublisherGroup):
    default_language = "kr"

    MBN = Publisher(
            name="MaeilBusinessNewspaper",
            domain="https://www.mk.co.kr/",
            parser=MBNParser,
            sources=[
                RSSFeed("https://www.mk.co.kr/rss/40300001/"),
            ],
        )
    
    """
    Newsis = Publisher(
            name="Newsis",
            domain="https://www.newsis.com/",
            parser=NewsisParser,
            sources=[
                RSSFeed("https://www.newsis.com/RSS/sokbo.xml"),
                Sitemap(
                    url="https://www.newsis.com/sitemap.xml",
                    recursive=True,
                    reverse=True,
                    sitemap_filter=inverse(regex_filter(
                        "/photo|/video|/people|/company|/arti_corner|/intro|/section|/list|/schedule|/gralist"
                    ))
                ),
                NewsMap("https://www.newsis.com/newsis_news_google.xml"),
            ],
        )
    """
