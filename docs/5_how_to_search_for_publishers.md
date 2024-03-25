# Table of Contents

* [How to search for publishers](#how-to-search-for-publishers)
  * [Using `search()`](#using-search)

# How to search for publishers

This tutorial will show you how to search for specific publishers in the `PublisherCollection`.

## Using `search()`

There are quite a few differences between the publishers, especially in the attributes the underlying parser supports.
You can search through the collection to get only publishers fitting your use case by utilizing the `search()` method.

Let's get some publishers based in the US, supporting an attribute called `topics` and `NewsMap` as a source, and use them to initialize a crawler afterward.

````python
from fundus import Crawler, PublisherCollection
from fundus.scraping.url import NewsMap

fitting_publishers = PublisherCollection.us.search(attributes=["topics"], source_types=[NewsMap])
crawler = Crawler(fitting_publishers)
````
