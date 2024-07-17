# Table of Contents

* [Advanced Topics](#advanced-topics)
  * [How to search for publishers](#how-to-search-for-publishers)
    * [Using `search()`](#using-search)
  * [Working with deprecated publishers](#working-with-deprecated-publishers)

# Advanced Topics

This tutorial will show further options such as searching for specific publishers in the `PublisherCollection` or dealing with deprecated ones.

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

## Working with deprecated publishers

When we notice that a publisher is uncrawlable for whatever reason, we will mark it with a deprecated flag.
This mostly has internal usages, since the default value for the `Crawler` `ignore_deprecated` flag is `False`.
You can alter this behaviour when initiating the `Crawler` and setting the `ignore_deprecated` flag.

In the [next section](6_logging.md) we introduce you to Fundus logging mechanics.