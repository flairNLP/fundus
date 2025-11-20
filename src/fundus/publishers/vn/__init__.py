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
      Sitemap("https://vnexpress.net/sitemap.xml"),
      NewsMap("https://vnexpress.net/google-news-sitemap.xml"),
    ],
    suppress_robots=True,
  )
