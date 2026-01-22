from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.vn.vnexpress import VnExpressIntlParser
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap


class VN(metaclass=PublisherGroup):
    default_language = "vi"

    VnExpress = Publisher(
        name="VnExpress",
        domain="https://vnexpress.net/",
        parser=VnExpressIntlParser,
        sources=[
            RSSFeed("https://vnexpress.net/rss/tin-moi-nhat.rss"),
            RSSFeed("https://vnexpress.net/rss/the-gioi.rss"),
            RSSFeed("https://vnexpress.net/rss/thoi-su.rss"),
            RSSFeed("https://vnexpress.net/rss/kinh-doanh.rss"),
            RSSFeed("https://vnexpress.net/rss/giai-tri.rss"),
            RSSFeed("https://vnexpress.net/rss/the-thao.rss"),
            RSSFeed("https://vnexpress.net/rss/phap-luat.rss"),
            RSSFeed("https://vnexpress.net/rss/giao-duc.rss"),
            RSSFeed("https://vnexpress.net/rss/tin-moi-nhat.rss"),
            RSSFeed("https://vnexpress.net/rss/tin-noi-bat.rss"),
            RSSFeed("https://vnexpress.net/rss/suc-khoe.rss"),
            RSSFeed("https://vnexpress.net/rss/gia-dinh.rss"),
            RSSFeed("https://vnexpress.net/rss/du-lich.rss"),
            RSSFeed("https://vnexpress.net/rss/khoa-hoc-cong-nghe.rss"),
            RSSFeed("https://vnexpress.net/rss/oto-xe-may.rss"),
            RSSFeed("https://vnexpress.net/rss/y-kien.rss"),
            RSSFeed("https://vnexpress.net/rss/tam-su.rss"),
        ],
        suppress_robots=True,
    )
