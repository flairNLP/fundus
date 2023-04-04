<img alt="alt text" src="resources/fundus_logo.png" width="180"/>

[![PyPI version](https://badge.fury.io/py/fundus.svg)](https://badge.fury.io/py/fundus)
[![GitHub Issues](https://img.shields.io/github/issues/flairNLP/fundus.svg)](https://github.com/flairNLP/fundus/issues)
[![Contributions welcome](https://img.shields.io/badge/contributions-welcome-brightgreen.svg)](CONTRIBUTING.md)
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

Let's use Fundus to crawl 2 articles of German-language news.

```python
from src.library.collection import PublisherCollection
from src.scraping.pipeline import Crawler

# initialize the crawler for German-language news
pipeline = Crawler(PublisherCollection.de)

# crawl 2 articles and print
for article in pipeline.crawl(max_articles=2):
    print(article)
```

This should print something like:

```console
Fundus-Article:
- Title: "VfL Wolfsburg - 1. FC Union Berlin Highlights: Zusammenfassung im Video - [...]"
- Text:  "Der VfL Wolfsburg erkämpft sich ein verdientes Remis gegen Union Berlin.
          Juranovic schießt die Köpenicker per Elfmeter in Führung. [...]"
- URL:    https://www.welt.de/sport/fussball/bundesliga/video244213079/VfL-Wolfsburg-1-FC-Union-Berlin-Highlights-Zusammenfassung-im-Video-Bundesliga.html
- From:   DieWelt (2023-03-12 21:40)

Fundus-Article:
- Title: "Herzensprojekt: Wie zwei Frauen aus Magdeburg Konzerte für kranke Kinder [...]"
- Text:  "Ein Aufenthalt im Krankenhaus ist nie schön. Für Kinder erst recht nicht. Für
          die Kleinsten ist der Alltag aus Operationen und Untersuchungen [...]"
- URL:    https://www.mdr.de/nachrichten/sachsen-anhalt/magdeburg/magdeburg/kinderklinikkonzerte-revolverheld-max-giesinger-ehrenamt-engagement-verein-100.html
- From:   MDR (2023-03-12 21:40)
```

This means that you crawled 2 articles from different German-language sources.

### Example 2: Crawl a specific news source

Maybe you want to crawl a specific news source instead. Let's crawl news articles form Berliner Zeitung only:

```python
from src.library.collection import PublisherCollection
from src.scraping.pipeline import Crawler

# initialize the crawler for German-language news
pipeline = Crawler(PublisherCollection.de.BerlinerZeitung)

# crawl 5 articles and print
for article in pipeline.crawl(max_articles=5):
    print(article)
```

## Tutorials

We provide **quick tutorials** to get you started with the library:

1. [**Tutorial 1: How to crawl news with Fundus**](/resources/docs/...)
2. [**Tutorial 2: The Article Class**](/resources/docs/...)
3. [**Tutorial 3: How to add a new news source**](/resources/docs/...)

The tutorials explain how ...

## Currently Supported News Sources

You can find the news sources currently supported [**here**](/doc/supported_news.md).

Also: **Adding a new source is easy - consider contributing to the project!**

## Contact

Please email your questions or comments to ...

## Contributing

Thanks for your interest in contributing! There are many ways to get involved;
start with our [contributor guidelines](CONTRIBUTING.md) and then
check these [open issues](https://github.com/flairNLP/fundus/issues) for specific tasks.

## [License](/LICENSE)

?