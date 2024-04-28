from fundus import PublisherCollection, Crawler

crawler = Crawler(PublisherCollection.uk.TheMirror)

for article in crawler.crawl(max_articles=2, only_complete=False):
    print(article.title)
    print(article.html.responded_url)
    print(article.publishing_date)
    print(article.authors)
    print(article.topics)
    print(article.plaintext)
    print("------ New Article ------:\n")
    