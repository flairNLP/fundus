from fundus import PublisherCollection, Crawler

# Change to:
# PublisherCollection.<country_section>.<publisher_specification>
publisher = PublisherCollection.de.Vogue

crawler = Crawler(publisher)

for article in crawler.crawl(max_articles=2):
    print(article)