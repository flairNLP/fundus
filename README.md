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

from src.fundus import PublisherCollection, Crawler

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

from src.fundus import PublisherCollection, Crawler

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

Fundus currently has support for the following news sources. We are constantly expanding the supported sources.

<table>
    <tr>
        <th>Source</th>
        <th>Domain</th>
        <th>Language</th>
        <th>Class</th>
    </tr>
    <tr>
        <td>Die Welt</td>
        <td>
            <a href="https://www.welt.de">
                <span>www.welt.de</span>
            </a>
        </td>
        <td>German</td>
        <td><code>DieWelt</code></td>
    </tr>
    <tr>
        <td>Berliner Zeitung</td>
        <td>
            <a href="https://www.berliner-zeitung.de">
                <span>www.berliner-zeitung.de</span>
            </a>
        </td>
        <td>German</td>
        <td><code>BerlinerZeitung</code></td>
    </tr>
    <tr>
        <td>Mitteldeutscher Rundfunk</td>
        <td>
            <a href="https://www.mdr.de">
                <span>www.mdr.de</span>
            </a>
        </td>
        <td>German</td>
        <td><code>MDR</code></td>
    </tr>
    <tr>
        <td>Frankfurter Allgemeine Zeitung</td>
        <td>
            <a href="https://www.faz.de">
                <span>www.faz.de</span>
            </a>
        </td>
        <td>German</td>
        <td><code>FAZ</code></td>
    </tr>
    <tr>
        <td>Focus Online</td>
        <td>
            <a href="https://www.focus.de">
                <span>www.focus.de</span>
            </a>
        </td>
        <td>German</td>
        <td><code>Focus</code></td>
    </tr>
    <tr>
        <td>Münchner Merkur</td>
        <td>
            <a href="https://www.merkur.de">
                <span>www.merkur.de</span>
            </a>
        </td>
        <td>German</td>
        <td><code>Merkur</code></td>
    </tr>
    <tr>
        <td>Süddeutsche Zeitung</td>
        <td>
            <a href="https://www.sueddeutsche.de/">
                <span>www.sueddeutsche.de</span>
            </a>
        </td>
        <td>German</td>
        <td><code>SZ</code></td>
    </tr>
    <tr>
        <td>Spiegel Online</td>
        <td>
            <a href="https://www.spiegel.de">
                <span>www.spiegel.de</span>
            </a>
        </td>
        <td>German</td>
        <td><code>SpiegelOnline</code></td>
    </tr>
    <tr>
        <td>Die Zeit</td>
        <td>
            <a href="https://www.zeit.de">
                <span>www.zeit.de</span>
            </a>
        </td>
        <td>German</td>
        <td><code>DieZeit</code></td>
    </tr>
    <tr>
        <td>Tagesschau</td>
        <td>
            <a href="https://www.tagesschau.de">
                <span>www.tagesschau.de</span>
            </a>
        </td>
        <td>German</td>
        <td><code>Tagesschau</code></td>
    </tr>
    <tr>
        <td>Deutsche Welle</td>
        <td>
            <a href="https://www.dw.de">
                <span>www.dw.de</span>
            </a>
        </td>
        <td>German</td>
        <td><code>DW</code></td>
    </tr>
    <tr>
        <td>ORF</td>
        <td>
            <a href="https://www.orf.de">
                <span>www.orf.de</span>
            </a>
        </td>
        <td>German</td>
        <td><code>ORF</code></td>
    </tr>
</table>

Also: **Adding a new source is easy - consider contributing to the project!**

## Contact

Please email your questions or comments to ...

## Contributing

Thanks for your interest in contributing! There are many ways to get involved;
start with our [contributor guidelines](CONTRIBUTING.md) and then
check these [open issues](https://github.com/flairNLP/fundus/issues) for specific tasks.

## [License](/LICENSE)

?