from fundus.publishers import PublisherCollection
from fundus.scraping.crawler import Crawler

publisher = PublisherCollection.tr.NTVTR

crawler = Crawler(publisher)

for article in crawler.crawl(max_articles=2, only_complete=False):
    print(article)
