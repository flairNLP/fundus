from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.vn.vnexpress import VnExpressIntlParser
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

EXCLUDED_PATTERNS = regex_filter("vnexpress.net/video/|vnexpress.net/anh/")


class VN(metaclass=PublisherGroup):
    """Publisher group for Vietnamese news sources"""

    default_language = "vi"

    VnExpress = Publisher(
        name="VnExpress",
        domain="https://vnexpress.net/",
        parser=VnExpressIntlParser,
        sources=[
            RSSFeed("https://vnexpress.net/rss/tin-moi-nhat.rss"),
            Sitemap("https://vnexpress.net/sitemap.xml"),
            NewsMap("https://vnexpress.net/google-news-sitemap.xml"),
        ],
        suppress_robots=True,
    )
