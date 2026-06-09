# Table of Contents

* [Advanced Topics](#advanced-topics)
  * [How to search for publishers](#how-to-search-for-publishers)
    * [Using `search()`](#using-search)
  * [Working with deprecated publishers](#working-with-deprecated-publishers)
  * [Filtering publishers for AI training](#filtering-publishers-for-ai-training)
  * [Browser impersonation](#browser-impersonation)

# Advanced Topics

This tutorial will show further options such as searching for specific publishers in the `PublisherCollection` or dealing with deprecated ones.

## How to search for publishers

### Using `search()`

There are quite a few differences between the publishers, especially in the attributes the underlying parser supports.
You can search through the collection to get only publishers fitting your use case by utilizing the `search()` method.

Let's get some publishers based in the US, supporting an attribute called `topics` and `NewsMap` as a source, and use them to initialize a crawler afterward.
The `search()` method also implements an internal language filter, allowing you to restrict your results to a specific languages.
In this example, we are only interested in Spanish articles.

````python
from fundus import Crawler, PublisherCollection, NewsMap

fitting_publishers = PublisherCollection.us.search(attributes=["topics"], source_types=[NewsMap], languages=["es"])
crawler = Crawler(*fitting_publishers)
````

## Working with deprecated publishers

When we notice that a publisher is uncrawlable for whatever reason, we will mark it with a deprecated flag.
This mostly has internal usages, since the default value for the `Crawler` `ignore_deprecated` flag is `False`.
You can alter this behaviour when initiating the `Crawler` and setting the `ignore_deprecated` flag.

## Filtering publishers for AI training

Some publishers explicitly disallow the use of their content for AI training purposes.
We _try_ to respect these wishes by introducing the `skip_publishers_disallowing_training` parameter in the `crawl()` function.
Users intending to use Fundus to gather training data for AI models should set this parameter to `True` to avoid collecting articles from publishers that wish for their content to not be used in this way.
Yet, as publishers are not required to mention this in their robots.txt file, users should additionally check the terms of use of the publishers they want to crawl and set the `disallows_training` attribute of the `Publisher` class accordingly.

## Browser impersonation

A small number of publishers gate their content behind anti-bot checks that inspect the TLS handshake and HTTP/2 fingerprint of the client.
Fundus can use [`curl_cffi`](https://github.com/lexiforest/curl_cffi) to mimic a real browser's fingerprint for these publishers, but because doing so is intended to bypass an explicit anti-bot signal we consider it an ethical gray area and leave it **off by default**.

To enable it, pass `impersonate=True` to the `Crawler`:

````python
from fundus import Crawler, PublisherCollection

crawler = Crawler(PublisherCollection, impersonate=True)
````

When `impersonate=False` (the default), Fundus issues requests with its regular user-agent and TLS fingerprint regardless of what a publisher declares.
Publishers that require impersonation will likely respond with 4xx/5xx in that case and simply produce no articles — Fundus does not skip them or warn about this.
When `impersonate=True`, each publisher's declared profile (e.g. `"chrome"`) is used; publishers without a declared profile are unaffected.

In the [next section](6_logging.md) we introduce you to Fundus logging mechanics.