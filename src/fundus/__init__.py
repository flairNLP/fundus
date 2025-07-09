import pathlib

from langdetect import DetectorFactory

from fundus.publishers import PublisherCollection
from fundus.scraping.article import Article
from fundus.scraping.crawler import CCNewsCrawler, Crawler, CrawlerBase
from fundus.scraping.filter import Requires
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

__module_path__ = pathlib.Path(__file__).parent
__development_base_path__ = __module_path__.parents[1]

__all__ = [
    "CrawlerBase",
    "Crawler",
    "CCNewsCrawler",
    "PublisherCollection",
    "Requires",
    "RSSFeed",
    "Sitemap",
    "NewsMap",
    "Article",
]

# make language detection deterministic https://pypi.org/project/langdetect/
DetectorFactory.seed = 0
