from fundus import PublisherCollection, Crawler

# Change to:
# PublisherCollection.<country_section>.<publisher_specification>
publisher = PublisherCollection.uk.TheMirror


crawler = Crawler(publisher)

for article in crawler.crawl(max_articles=2, only_complete=False):
    print(article)
# print(dir(PublisherCollection.uk))