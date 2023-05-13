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

### Example 2: Crawl a specific news source

Maybe you want to crawl a specific news source instead. Let's crawl news articles form Washington Times only:

```python

from fundus import PublisherCollection, Crawler

# initialize the crawler for Washington Times
crawler = Crawler(PublisherCollection.us.WashingtonTimes)

# crawl 5 articles and print
for article in pipeline.crawl(max_articles=5):
    print(article)
```

## Tutorials

We provide **quick tutorials** to get you started with the library:

1. [**Tutorial 1: How to crawl news with Fundus**](docs/...)
2. [**Tutorial 2: The Article Class**](docs/...)
3. [**Tutorial 3: How to add a new news-source**](docs/how_to_contribute.md)

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
            <a href="https://www.welt.de/">
                <span>www.welt.de/</span>
            </a>
        </td>
        <td>German</td>
        <td><code>DieWelt</code></td>
        </tr>
 <tr>
        <td> MDR</td>
        <td>
            <a href="https://www.mdr.de/">
                <span>www.mdr.de/</span>
            </a>
        </td>
        <td>German</td>
        <td><code>MDR</code></td>
        </tr>
 <tr>
        <td> FAZ</td>
        <td>
            <a href="https://www.faz.net/">
                <span>www.faz.net/</span>
            </a>
        </td>
        <td>German</td>
        <td><code>FAZ</code></td>
        </tr>
 <tr>
        <td> Focus</td>
        <td>
            <a href="https://www.focus.de/">
                <span>www.focus.de/</span>
            </a>
        </td>
        <td>German</td>
        <td><code>Focus</code></td>
        </tr>
 <tr>
        <td> Merkur</td>
        <td>
            <a href="https://www.merkur.de/">
                <span>www.merkur.de/</span>
            </a>
        </td>
        <td>German</td>
        <td><code>Merkur</code></td>
        </tr>
 <tr>
        <td> SZ</td>
        <td>
            <a href="https://www.sueddeutsche.de/">
                <span>www.sueddeutsche.de/</span>
            </a>
        </td>
        <td>German</td>
        <td><code>SZ</code></td>
        </tr>
 <tr>
        <td> SpiegelOnline</td>
        <td>
            <a href="https://www.spiegel.de/">
                <span>www.spiegel.de/</span>
            </a>
        </td>
        <td>German</td>
        <td><code>SpiegelOnline</code></td>
        </tr>
 <tr>
        <td> DieZeit</td>
        <td>
            <a href="https://www.sueddeutsche.de/">
                <span>www.sueddeutsche.de/</span>
            </a>
        </td>
        <td>German</td>
        <td><code>DieZeit</code></td>
        </tr>
 <tr>
        <td> BerlinerZeitung</td>
        <td>
            <a href="https://www.sueddeutsche.de/">
                <span>www.sueddeutsche.de/</span>
            </a>
        </td>
        <td>German</td>
        <td><code>BerlinerZeitung</code></td>
        </tr>
 <tr>
        <td> Tagesschau</td>
        <td>
            <a href="https://www.tagesschau.de/">
                <span>www.tagesschau.de/</span>
            </a>
        </td>
        <td>German</td>
        <td><code>Tagesschau</code></td>
        </tr>
 <tr>
        <td> DW</td>
        <td>
            <a href="https://www.dw.com/">
                <span>www.dw.com/</span>
            </a>
        </td>
        <td>German</td>
        <td><code>DW</code></td>
        </tr>
 <tr>
        <td> Stern</td>
        <td>
            <a href="https://www.stern.de/">
                <span>www.stern.de/</span>
            </a>
        </td>
        <td>German</td>
        <td><code>Stern</code></td>
        </tr>
 <tr>
        <td> NTV</td>
        <td>
            <a href="https://www.ntv.de/">
                <span>www.ntv.de/</span>
            </a>
        </td>
        <td>German</td>
        <td><code>NTV</code></td>
        </tr>
 <tr>
        <td> NDR</td>
        <td>
            <a href="https://www.ndr.de/">
                <span>www.ndr.de/</span>
            </a>
        </td>
        <td>German</td>
        <td><code>NDR</code></td>
        </tr>
 <tr>
        <td> Taz</td>
        <td>
            <a href="https://www.taz.de/">
                <span>www.taz.de/</span>
            </a>
        </td>
        <td>German</td>
        <td><code>Taz</code></td>
        </tr>
 <tr>
        <td> Bild</td>
        <td>
            <a href="https://www.bild.de/">
                <span>www.bild.de/</span>
            </a>
        </td>
        <td>German</td>
        <td><code>Bild</code></td>
        </tr>

 <tr>
        <td> ORF</td>
        <td>
            <a href="https://www.orf.at">
                <span>www.orf.at</span>
            </a>
        </td>
        <td>At</td>
        <td><code>ORF</code></td>
        </tr>

 <tr>
        <td> APNews</td>
        <td>
            <a href="https://apnews.com/">
                <span>apnews.com/</span>
            </a>
        </td>
        <td>Us</td>
        <td><code>APNews</code></td>
        </tr>
 <tr>
        <td> CNBC</td>
        <td>
            <a href="https://www.cnbc.com/">
                <span>www.cnbc.com/</span>
            </a>
        </td>
        <td>Us</td>
        <td><code>CNBC</code></td>
        </tr>
 <tr>
        <td> TheIntercept</td>
        <td>
            <a href="https://theintercept.com/">
                <span>theintercept.com/</span>
            </a>
        </td>
        <td>Us</td>
        <td><code>TheIntercept</code></td>
        </tr>
 <tr>
        <td> TheGatewayPundit</td>
        <td>
            <a href="https://www.thegatewaypundit.com/">
                <span>www.thegatewaypundit.com/</span>
            </a>
        </td>
        <td>Us</td>
        <td><code>TheGatewayPundit</code></td>
        </tr>
 <tr>
        <td> FoxNews</td>
        <td>
            <a href="https://foxnews.com/">
                <span>foxnews.com/</span>
            </a>
        </td>
        <td>Us</td>
        <td><code>FoxNews</code></td>
        </tr>
 <tr>
        <td> TheNation</td>
        <td>
            <a href="https://www.thenation.com/">
                <span>www.thenation.com/</span>
            </a>
        </td>
        <td>Us</td>
        <td><code>TheNation</code></td>
        </tr>
 <tr>
        <td> WorldTruth</td>
        <td>
            <a href="https://worldtruth.tv/">
                <span>worldtruth.tv/</span>
            </a>
        </td>
        <td>Us</td>
        <td><code>WorldTruth</code></td>
        </tr>
 <tr>
        <td> FreeBeacon</td>
        <td>
            <a href="https://freebeacon.com/">
                <span>freebeacon.com/</span>
            </a>
        </td>
        <td>Us</td>
        <td><code>FreeBeacon</code></td>
        </tr>
 <tr>
        <td> WashingtonTimes</td>
        <td>
            <a href="https://www.washingtontimes.com/">
                <span>www.washingtontimes.com/</span>
            </a>
        </td>
        <td>Us</td>
        <td><code>WashingtonTimes</code></td>
        </tr>

</table>

Also: **Adding a new source is easy - consider contributing to the project!**

## Contact

Please email your questions or comments to ...

## Contributing

Thanks for your interest in contributing! There are many ways to get involved;
start with our [contributor guidelines](docs/how_to_contribute.md) and then
check these [open issues](https://github.com/flairNLP/fundus/issues) for specific tasks.

## [License](/LICENSE)

?
