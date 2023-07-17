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

**_NOTE:_** To build a pipeline from low-level `Scraper` objects make use of the `BaseCrawler` class.

# How to crawl articles

Now to crawl articles make use of the `crawl()` method of the initialized crawler class.
Calling this will return an `Iterator` over articles.

Let's crawl one news article from all publishers based in the US.

````python
from fundus import PublisherCollection, Crawler

# initialize the crawler for news publishers based in the US
crawler = Crawler(PublisherCollection.us)

# crawl 2 articles and print
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
# crawl 2 articles and print
for article in crawler.crawl():
    print(article)
````

In the [next section](2_the_article_class.md) we will introduce you to the `Article` class.
