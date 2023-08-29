<img alt="alt text" src="resources/fundus_logo.png" width="180"/>

[![PyPI version](https://badge.fury.io/py/fundus.svg)](https://badge.fury.io/py/fundus)
[![GitHub Issues](https://img.shields.io/github/issues/flairNLP/fundus.svg)](https://github.com/flairNLP/fundus/issues)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](docs/how_to_contribute.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)](https://opensource.org/licenses/MIT)

A very simple **news crawler**.
Developed at [Humboldt University of Berlin](https://www.informatik.hu-berlin.de/en/forschung-en/gebiete/ml-en/).

---

Fundus is:

* **A static news crawler.** 
  Fundus lets you gather a ton of news articles already in shape from a huge variety of news sources in only a couple of lines of code.
  Be it for your thesis about political bias or training your home-brewed stock prediction model, Fundus gets you covered with the data.

* **An open-source Python package.**
  Fundus is built around and based on the idea of building something together.
  The more people want to be a part of this the better. So feel free to check out if you can help Fundus [growing](docs/how_to_contribute.md)

## Quick Start

### Requirements and Installation

In your favorite virtual environment, simply do:

```
pip install fundus
```

Fundus requires Python 3.8+.

### Example 1: Crawl a bunch of English-language news articles

Let's use Fundus to crawl 2 articles from publishers based in the US.

```python
from fundus import PublisherCollection, Crawler

# initialize the crawler for news publishers based in the US
crawler = Crawler(PublisherCollection.us)

# crawl 2 articles and print
for article in crawler.crawl(max_articles=2):
    print(article)
```

This should print something like this:

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

### Example 2: Crawl a specific news source

Maybe you want to crawl a specific news source instead. Let's crawl news articles from Washington Times only:

```python

from fundus import PublisherCollection, Crawler

# initialize the crawler for Washington Times
crawler = Crawler(PublisherCollection.us.WashingtonTimes)

# crawl 5 articles and print
for article in crawler.crawl(max_articles=2):
    print(article)
```

## Tutorials

We provide **quick tutorials** to get you started with the library:

1. [**Tutorial 1: How to crawl news with Fundus**](docs/1_getting_started.md)
2. [**Tutorial 2: The Article Class**](docs/2_the_article_class.md)
3. [**Tutorial 3: How to filter articles**](docs/3_how_to_filter_articles.md)
4. [**Tutorial 4: How to search for publishers**](docs/4_how_to_search_for_publishers.md)

If you wish to contribute check out these tutorials
1. [**How to contribute**](docs/how_to_contribute.md)
2. [**How to add a publisher**](docs/how_to_add_a_publisher.md)

## Currently Supported News Sources

You can find the publishers currently supported [**here**](/docs/supported_publishers.md).

Also: **Adding a new publisher is easy - consider contributing to the project!**

## Contact

Please email your questions or comments to [**Max Dallabetta**](mailto:max.dallebtta@googlemail.com?subject=[GitHub]%20Fundus)

## Contributing

Thanks for your interest in contributing! There are many ways to get involved;
start with our [contributor guidelines](docs/how_to_contribute.md) and then
check these [open issues](https://github.com/flairNLP/fundus/issues) for specific tasks.

## License

[MIT](LICENSE)