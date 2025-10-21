from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.lb.lbc_group import LBCGroupParser
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

class LB(metaclass=PublisherGroup):
    default_language= "ar"

    LBCGroup=Publisher(
        name = "LBC",
        domain = "https://www.lbcgroup.tv",
        parser = LBCGroupParser,
        sources=[
            RSSFeed("https://www.lbcgroup.tv/Rss/latest-news/en"),
            NewsMap("https://www.lbcgroup.tv/newssitemap.xml"),
            Sitemap("https://www.lbcgroup.tv/sitemap.xml"),
        ],
    )
