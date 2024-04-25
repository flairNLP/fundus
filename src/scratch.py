from fundus import PublisherCollection, Crawler

# Change to:
# PublisherCollection.<country_section>.<publisher_specification>
publisher = PublisherCollection.de.RBB24

crawler = Crawler(publisher)

for article in crawler.crawl(max_articles=10, only_complete=False):
    print(article)
