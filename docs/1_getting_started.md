# Basics

This tutorial explains the basic concepts of Fundus:
- What is the `PublisherCollection`
- What is a `Crawler`
- How to retrieve articles

## `PublisherCollection`

Fundus comes with a collection of publisher-specific parsers grouped by country of origin.
You can access these publishers through a single class called `PublisherCollection` using the [Alpha-2](https://www.iban.com/country-codes) codes described in ISO 3166 as identifiers.
The `PublisherCollection` works as an information hub describing publishers [currently supported](supported_publishers.md) by Fundus.

For example, to access all publishers based in the US simply write:
````python
from fundus import PublisherCollection

PublisherCollection.us
````

## The crawler

If you want to crawl articles, you need to initialize a crawler first.
You can do so by using the publisher collection (recommended) or low-level objects.

As an example, let's initiate a crawler capable of crawling publishers based in the US by utilizing the `PublisherCollection`

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

As an example let us crawl one news article from all publishers based in the US.

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

**_NOTE:_** There is also an `async` access point for crawling called `crawl_async`. 
If you want to crawl articles within any async workflow we highly recommend using this instead.
This async access point will return an `AsyncIterator[Article]`.

In the [next section](2_the_article_class.md) we will introduce you to the `Article` class.