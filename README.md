<img alt="alt text" src="resources/fundus_logo.png" width="180"/>

[![PyPI version](https://badge.fury.io/py/fundus.svg)](https://badge.fury.io/py/fundus)
[![GitHub Issues](https://img.shields.io/github/issues/flairNLP/fundus.svg)](https://github.com/flairNLP/fundus/issues)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](docs/how_to_contribute.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)](https://opensource.org/licenses/MIT)

A very simple **news crawler**.
Developed at [Humboldt University of Berlin](https://www.informatik.hu-berlin.de/en/forschung-en/gebiete/ml-en/).

---

Fundus is:

* A crawler for news ...

* A Python ...

## Quick Start

### Requirements and Installation

In your favorite virtual environment, simply do:

```
pip install fundus
```

Fundus requires Python 3.8+.

### Example 1: Crawl a bunch of German-language news articles

Let's use Fundus to crawl 2 articles of English-language news publishers based in the US.

```python

from fundus import PublisherCollection, Crawler

# initialize the crawler for news publisher based in the us
crawler = Crawler(PublisherCollection.us)

# crawl 2 articles and print
for article in crawler.crawl(max_articles=2):
    print(article)
```

This should print something like:

```console
Fundus-Article:
- Title: "Feinstein's Return Not Enough for Confirmation of Controversial New [...]"
- Text:  "Democrats jammed three of President Joe Biden's controversial court nominees
          through committee votes on Thursday thanks to a last-minute [...]"
- URL:    https://freebeacon.com/politics/feinsteins-return-not-enough-for-confirmation-of-controversial-new-hampshire-judicial-nominee/
- From:   FreeBeacon (2023-05-11 18:41)
Fundus-Article:
- Title: "Northwestern student government freezes College Republicans funding over [...]"
- Text:  "Student government at Northwestern University in Illinois "indefinitely" froze
          the funds of the university's chapter of College Republicans [...]"
- URL:    https://www.foxnews.com/us/northwestern-student-government-freezes-college-republicans-funding-poster-critical-lgbtq-community
- From:   FoxNews (2023-05-09 14:37)
```

This means that you crawled 2 articles from different US publishers.

### Example 2: Crawl specific news source

Maybe you want to crawl a specific news source instead. Let's crawl news articles form Washington Times only:

```python

from fundus import PublisherCollection, Crawler

# initialize the crawler for Washington Times
crawler = Crawler(PublisherCollection.us.WashingtonTimes)

# crawl 5 articles and print
for article in crawler.crawl(max_articles=5):
    print(article)
```

## Tutorials

We provide **quick tutorials** to get you started with the library:

1. [**Tutorial 1: How to crawl news with Fundus**](docs/...)
2. [**Tutorial 2: The Article Class**](docs/...)
3. [**Tutorial 3: How to add a new news-source**](docs/how_to_contribute.md)

The tutorials explain how ...

## Currently Supported News Sources

You can find the publishers currently supported [**here**](/docs/supported_publishers.md).

Also: **Adding a new source is easy - consider contributing to the project!**

## Contact

Please email your questions or comments to ...

## Contributing

Thanks for your interest in contributing! There are many ways to get involved;
start with our [contributor guidelines](docs/how_to_contribute.md) and then
check these [open issues](https://github.com/flairNLP/fundus/issues) for specific tasks.

## [License](/LICENSE)

[MIT](LICENSE)