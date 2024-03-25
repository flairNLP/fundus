# Table of Contents

* [How to crawl articles from CC-NEWS](#how-to-crawl-articles-from-cc-news)
  * [The crawler](#the-crawler)
    * [OS start method](#os-start-method)
  * [Date range](#date-range)
  * [Multiprocessing](#multiprocessing)

# How to crawl articles from CC-NEWS

This tutorial explains how to crawl articles from the [CC-NEWS](https://paperswithcode.com/dataset/cc-news) dataset using Fundus.

## The crawler

To crawl articles from CC-NEWS simply import the `CCNewsCrawler` and stick to the same schema as with the main Fundus crawler.
Now let's crawl a bunch of news articles from CC-NEWS using all available publishers supported in the Fundus `PublisherCollection`.

````python
from fundus import CCNewsCrawler, PublisherCollection

crawler = CCNewsCrawler(*PublisherCollection)
for article in crawler.crawl(max_articles=100):
    print(article)
````

### OS start method
Depending on the process [start method](https://docs.python.org/3/library/multiprocessing.html#contexts-and-start-methods) used by your OS, you may have to wrap this crawl with a `__name__ == "__main__"` block.

````python
from fundus import CCNewsCrawler, PublisherCollection

if __name__ == "__main__":
    crawler = CCNewsCrawler(*PublisherCollection)
    for article in crawler.crawl(max_articles=100):
        print(article)
````

This code will crawl 100 random articles from the entire date range of the CC-NEWS dataset.

## Date range

Date range you may ask?
Yes, you can specify a date range corresponding to the date the article was added to CC-NEWS.
Let's crawl some articles that were crawled between 2020/01/01 and 2020/03/03.

````python
from datetime import datetime

from fundus import CCNewsCrawler, PublisherCollection

crawler = CCNewsCrawler(*PublisherCollection, start=datetime(2020, 1, 1), end=datetime(2020, 3, 1))
for article in crawler.crawl(max_articles=100):
    print(article)
````

## Multiprocessing

The CC-NEWS dataset consists of multiple terabytes of articles.
Due to the sheer amount of data, the crawler utilizes multiple processes.
Per default, it uses all CPUs available in your system.
You can alter the number of additional processes used for crawling with the `processes` parameter of `CCNewsCrawler`.

````python
from fundus import CCNewsCrawler, PublisherCollection

crawler = CCNewsCrawler(*PublisherCollection, processes=4)
````

To omit multiprocessing, pass `-1` to the `processes` parameter.

In the [next section](3_the_article_class.md) we will introduce you to the `Article` class.

