# Table of Contents

* [How to search for publishers](#how-to-search-for-publishers)
  * [Using `search()`](#using-search)
* [Saving the crawled articles](#saving-the-crawled-articles)

# Advanced Topics

This tutorial will show further options such as searching for specific publishers in the `PublisherCollection` or saving the crawled articles.

## How to search for publishers

### Using `search()`

There are quite a few differences between the publishers, especially in the attributes the underlying parser supports.
You can search through the collection to get only publishers fitting your use case by utilizing the `search()` method.

Let's get some publishers based in the US, supporting an attribute called `topics` and `NewsMap` as a source, and use them to initialize a crawler afterward.

````python
from fundus import Crawler, PublisherCollection, NewsMap

fitting_publishers = PublisherCollection.us.search(attributes=["topics"], source_types=[NewsMap])
crawler = Crawler(fitting_publishers)
````

## Saving the crawled articles

When trying to save all parsed articles within a single file, the `crawl()` function provides the `save_to_file` parameter.
The parameter can be assigned a filepath specifying the location for the articles to be saved.