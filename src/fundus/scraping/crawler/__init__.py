from fundus.scraping.crawler.base import CrawlerBase, supports_attributes
from fundus.scraping.crawler.ccnews import CCNewsCrawler
from fundus.scraping.crawler.web import Crawler

__all__ = ["CrawlerBase", "Crawler", "CCNewsCrawler", "supports_attributes"]
