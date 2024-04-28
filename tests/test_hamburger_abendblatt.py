import urllib.request
from fundus import PublisherCollection, Crawler

# url = "https://www.abendblatt.de/"

# with urllib.request.urlopen(url) as response:
#     pass

publisher = PublisherCollection.de.HamburgerAbendblatt

crawler = Crawler(publisher)

for article in crawler.crawl(max_articles=10, only_complete=False):
    print(article)