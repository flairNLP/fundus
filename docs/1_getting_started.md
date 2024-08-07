# Table of Contents

* [Basics](#basics)
  * [What is the `PublisherCollection`](#what-is-the-publishercollection)
  * [What is a `Crawler`](#what-is-a-crawler)
* [How to crawl articles](#how-to-crawl-articles)
* [Saving crawled articles](#saving-crawled-articles)

# Basics

This tutorial explains the basic concepts of Fundus:
- What is the `PublisherCollection`
- What is a `Crawler`
- How to crawl articles

## What is the `PublisherCollection`

Fundus includes a collection of publisher-specific parsers grouped by country of origin.
You can access these publishers through a single class called `PublisherCollection` using the [Alpha-2](https://www.iban.com/country-codes) codes described in ISO 3166 as identifiers.
You can see which publishers are currently supported by Fundus [here](supported_publishers.md).

To access all publishers based in the US simply write:

````python
from fundus import PublisherCollection

PublisherCollection.us
````

## What is a `Crawler`

The `Crawler` is Fundus' main pipeline for crawling articles from supported publishers.
If you want to crawl articles, the first step is to initialize a crawler.
You can do so by making use of the `PublisherCollection`.

Let's initiate a crawler capable of crawling publishers based in the US.

````python
from fundus import PublisherCollection, Crawler

crawler = Crawler(PublisherCollection.us)
````

You can also initialize a crawler for the entire publisher collection

```` python
crawler = Crawler(PublisherCollection)
````

# How to crawl articles

Now to crawl articles make use of the `crawl()` method of the initialized crawler class.
Calling this will return an `Iterator` over articles.

Let's crawl one news article from a publisher based in the US and print it.

````python
from fundus import PublisherCollection, Crawler

# initialize the crawler for news publishers based in the US
crawler = Crawler(PublisherCollection.us)

# crawl one article from a publisher based in the US and print it
for article in crawler.crawl(max_articles=1):
    print(article)
````

This should print something like this:

```console
Fundus-Article:
- Title: "Feinstein's Return Not Enough for Confirmation of Controversial New [...]"
- Text:  "Democrats jammed three of President Joe Biden's controversial court nominees
          through committee votes on Thursday thanks to a last-minute [...]"
- URL:    https://freebeacon.com/politics/feinsteins-return-not-enough-for-confirmation-of-controversial-new-hampshire-judicial-nominee/
- From:   FreeBeacon (2023-05-11 18:41)
```

You can also crawl all available articles by simply removing the `max_articles` parameter.

```` python
# crawl all available articles
for article in crawler.crawl():
    print(article)
````

Additionally, you can set a timeout for the crawler in seconds.
If the crawler does not receive a new article within the specified timeout period, it will terminate automatically.
```` python
for article in crawler.crawl(timeout=10):
    print(article)
````
This is especially useful when working with date-related article filters.
Refer to [this section](4_how_to_filter_articles.md) to learn more about how to filter articles.

# Saving crawled articles

To save all crawled articles to a file use the `save_to_file` parameter of the `crawl` method.
When given a path, the crawled articles will be saved as a JSON list using the 
[default article serialization](3_the_article_class.md#saving-an-article) and `UTF-8` encoding.

In the [next](2_crawl_from_cc_news.md) section we will show you how to crawl articles from the CC-NEWS dataset.