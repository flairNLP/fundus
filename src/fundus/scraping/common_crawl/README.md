# CCNewsCrawler quick guide

This package provides functionality to crawl the [CC-NEWS](https://paperswithcode.com/dataset/cc-news) dataset for publishers supported by Fundus.
To use this crawler simply stick to the same schema as with the main Fundus crawler.

Let's crawl a bunch of news articles using the whole `PublisherCollection`

````python
from fundus import CCNewsCrawler, PublisherCollection

crawler = CCNewsCrawler(*PublisherCollection)
for article in crawler.crawl(max_articles=100):
    print(article)
````

Depending on the process [start methode](https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods) used by your os you may have to wrap this crawl into `__name__ == "__main__"`.

````python
from fundus import CCNewsCrawler, PublisherCollection

if __name__ == "__main__":
    crawler = CCNewsCrawler(*PublisherCollection)
    for article in crawler.crawl(max_articles=100):
        print(article)
````

This will crawl 100 random articles from the entire date range of the CC-NEWS dataset.
Date range you may ask?
Yes, you can specify a date range corresponding to the crawl date of collected articles.

Let's crawl some articles that were crawled between 2020/01/01 and 2020/03/03.

````python
from fundus import CCNewsCrawler, PublisherCollection
from datetime import datetime

crawler = CCNewsCrawler(*PublisherCollection)
for article in crawler.crawl(start=datetime(2020, 1, 1), end=datetime(2020, 3, 1), max_articles=100):
    print(article)
````

Due to the sheer amount of data, the crawler utilizes multiple processes.
Per default, the number of processes is equal to `os.cpu_count()`.
You can alter the number of processes used with the `processes` parameter.

````python
from fundus import CCNewsCrawler, PublisherCollection

crawler = CCNewsCrawler(*PublisherCollection, processes=4)
````

Currently, the `CCNEwsCrawler` is only implemented in a multiprocessing manner, but there will be a single process variant later on.

This crawler also supports all other parameters (extraction filtering, URL filtering, etc.) introduced with the basic fundus crawler.
Refer to the [tutorial](../../../../docs/1_getting_started.md) for an overview of how to use these parameters.
