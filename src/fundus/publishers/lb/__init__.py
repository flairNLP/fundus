from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.lb.lbc_group import LBCGroupParser
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap


class LB(metaclass=PublisherGroup):
    default_language = "ar"

    LBCGroup = Publisher(
        name="LBC",
        domain="https://www.lbcgroup.tv",
        parser=LBCGroupParser,
        sources=[
            RSSFeed("https://www.lbcgroup.tv/Rss/latest-news/en", languages={"en"}),
            RSSFeed("https://www.lbcgroup.tv/Rss/NewsHighlights/en", languages={"en"}),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/en/2/breaking-headlines", languages={"en"}),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/en/8/lebanon-news", languages={"en"}),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/en/125/world-news", languages={"en"}),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/en/126/middle-east-news", languages={"en"}),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/en/127/sports-news", languages={"en"}),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/en/128/variety-and-tech", languages={"en"}),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/en/131/israel-gaza-war-updates", languages={"en"}),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/en/104/lebanon-economy", languages={"en"}),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/en/122/press-highlights", languages={"en"}),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/en/66/news-bulletin-reports", languages={"en"}),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/ar/29/%D9%85%D9%86%D9%88%D8%B9%D8%A7%D8%AA"),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/ar/24/%D8%B5%D8%AD%D8%A9-%D9%88%D8%AA%D8%BA%D8%B0%D9%8A%D8%A9"),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/ar/25/%D8%A7%D9%82%D8%AA%D8%B5%D8%A7%D8%AF"),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/ar/123/%D8%AE%D8%A8%D8%B1-%D8%B9%D8%A7%D8%AC%D9%84"),
            RSSFeed(
                "https://www.lbcgroup.tv/Rss/News/ar/49/%D8%B9%D9%84%D9%88%D9%85-%D9%88%D8%AA%D9%83%D9%86%D9%88%D9%84%D9%88%D8%AC%D9%8A%D8%A7"
            ),
            RSSFeed(
                "https://www.lbcgroup.tv/Rss/News/ar/6/%D8%A3%D8%AE%D8%A8%D8%A7%D8%B1-%D8%AF%D9%88%D9%84%D9%8A%D8%A9"
            ),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/ar/7/%D8%A7%D8%B3%D8%B1%D8%A7%D8%B1"),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/ar/55/%D9%85%D9%88%D8%B6%D8%A9-%D9%88%D8%AC%D9%85%D8%A7%D9%84"),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/ar/54/%D8%B9%D8%A7%D9%84%D9%85-%D8%A7%D9%84%D8%B7%D8%A8%D8%AE"),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/ar/88/%D8%AE%D8%A8%D8%B1-%D9%83%D8%A7%D8%B0%D8%A8"),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/ar/5/%D8%B5%D8%AD%D9%81-%D8%A7%D9%84%D9%8A%D9%88%D9%85"),
            RSSFeed("https://www.lbcgroup.tv/Rss/latest-news/ar"),
            RSSFeed("https://www.lbcgroup.tv/Rss/NewsHighlights/ar"),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/ar/107/%D8%B1%D9%8A%D8%A7%D8%B6%D8%A9"),
            RSSFeed(
                "https://www.lbcgroup.tv/Rss/News/ar/1/%D8%A3%D8%AE%D8%A8%D8%A7%D8%B1-%D9%84%D8%A8%D9%86%D8%A7%D9%86"
            ),
            RSSFeed(
                "https://www.lbcgroup.tv/Rss/News/ar/129/%D8%A7%D9%84%D8%B3%D9%8A%D8%A7%D8%AD%D8%A9-%D9%81%D9%8A-%D9%84%D8%A8%D9%86%D8%A7%D9%86"
            ),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/ar/130/%D8%AB%D9%82%D8%A7%D9%81%D8%A9"),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/ar/3/%D8%A3%D9%85%D9%86-%D9%88%D9%82%D8%B6%D8%A7%D8%A1"),
            RSSFeed(
                "https://www.lbcgroup.tv/Rss/News/ar/65/%D8%AA%D9%82%D8%A7%D8%B1%D9%8A%D8%B1-%D9%86%D8%B4%D8%B1%D8%A9-%D8%A7%D9%84%D8%A7%D8%AE%D8%A8%D8%A7%D8%B1"
            ),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/ar/33/%D9%81%D9%86%D9%91"),
            RSSFeed(
                "https://www.lbcgroup.tv/Rss/News/ar/101/%D8%A7%D8%AE%D8%A8%D8%A7%D8%B1-%D8%A7%D9%84%D8%A8%D8%B1%D8%A7%D9%85%D8%AC"
            ),
            RSSFeed("https://www.lbcgroup.tv/Rss/News/ar/27/%D8%AD%D8%A7%D9%84-%D8%A7%D9%84%D8%B7%D9%82%D8%B3"),
            NewsMap("https://www.lbcgroup.tv/newssitemap.xml", languages={"en", "ar"}),
        ],
    )
