import datetime
import logging
from datetime import datetime

from fundus import Crawler, PublisherCollection
from fundus.logging import set_log_level


if __name__ == "__main__":
    skip = False
    for publisher in PublisherCollection:
        if skip or publisher.deprecated:
            if publisher.__name__ == "Merkur":
                skip = False
            continue
        crawler = Crawler(publisher)
        set_log_level(logging.WARN)
        with open("urls.txt", "w") as file:
            for article in crawler.crawl(max_articles=1, only_complete=False, error_handling="raise"):
                print(article.html.responded_url)
                print(article.images)
                if article.images:
                    file.write(article.images[0].urls[0])
                print("----------------------------------------------")
"""

publisher = PublisherCollection.de.DieWelt
crawler = Crawler(publisher)
for article in crawler.crawl(max_articles=10, only_complete=False, error_handling="raise"):
    print(article.html.responded_url)
    print(article.images)
"""