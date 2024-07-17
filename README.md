<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://github.com/flairNLP/fundus/blob/master/resources/logo/svg/logo_darkmode_with_font_and_clear_space.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://github.com/flairNLP/fundus/blob/master/resources/logo/svg/logo_lightmode_with_font_and_clear_space.svg">
    <img src="https://github.com/flairNLP/fundus/blob/master/resources/logo/svg/logo_lightmode_with_font_and_clear_space.svg" alt="Logo" width="50%" height="50%">
  </picture>
</p>

<p align="center">A very simple <b>news crawler</b> in Python.
Developed at <a href="https://www.informatik.hu-berlin.de/en/forschung-en/gebiete/ml-en/">Humboldt University of Berlin</a>.
</p>
<p align="center">
<a href="https://pypi.org/project/fundus/"><img alt="PyPi version" src="https://badge.fury.io/py/fundus.svg"></a>
<img alt="python" src="https://img.shields.io/badge/python-3.8-blue">
<img alt="Static Badge" src="https://img.shields.io/badge/license-MIT-green">
<img alt="Publisher Coverage" src="https://img.shields.io/endpoint?url=https://gist.githubusercontent.com/dobbersc/ca0ae056b05cbfeaf30fa42f84ddf458/raw/fundus_publisher_coverage.json">
</p>
<div align="center">
<hr>

[Quick Start](#quick-start) | [Tutorials](#tutorials) | [News Sources](/docs/supported_publishers.md) | [Paper](https://arxiv.org/abs/2403.15279)

</div>


---

Fundus is:

* **A static news crawler.** 
  Fundus lets you crawl online news articles with only a few lines of Python code!
  Be it from live websites or the CC-NEWS dataset.

* **An open-source Python package.**
  Fundus is built on the idea of building something together. 
  We welcome your contribution to  help Fundus [grow](docs/how_to_contribute.md)!

<hr>

## Quick Start

To install from pip, simply do:

```
pip install fundus
```

Fundus requires Python 3.8+.


## Example 1: Crawl a bunch of English-language news articles

Let's use Fundus to crawl 2 articles from publishers based in the US.

```python
from fundus import PublisherCollection, Crawler

# initialize the crawler for news publishers based in the US
crawler = Crawler(PublisherCollection.us)

# crawl 2 articles and print
for article in crawler.crawl(max_articles=2):
    print(article)
```

That's already it!

If you run this code, it should print out something like this:

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

This printout tells you that you successfully crawled two articles!

For each article, the printout details:
- the "Title" of the article, i.e. its headline 
- the "Text", i.e. the main article body text
- the "URL" from which it was crawled
- the news source it is "From"


## Example 2: Crawl a specific news source

Maybe you want to crawl a specific news source instead. Let's crawl news articles from Washington Times only:

```python
from fundus import PublisherCollection, Crawler

# initialize the crawler for The New Yorker
crawler = Crawler(PublisherCollection.us.TheNewYorker)

# crawl 2 articles and print
for article in crawler.crawl(max_articles=2):
    print(article)
```

## Example 3: Crawl 1 Million articles

To crawl such a vast amount of data, Fundus relies on the `CommonCrawl` web archive, in particular the news crawl `CC-NEWS`.
If you're not familiar with [`CommonCrawl`](https://commoncrawl.org/) or [`CC-NEWS`](https://commoncrawl.org/blog/news-dataset-available) check out their websites.
Simply import our `CCNewsCrawler` and make sure to check out our [tutorial](docs/2_crawl_from_cc_news.md) beforehand.

````python
from fundus import PublisherCollection, CCNewsCrawler

# initialize the crawler using all publishers supported by fundus
crawler = CCNewsCrawler(*PublisherCollection)

# crawl 1 million articles and print
for article in crawler.crawl(max_articles=1000000):
  print(article)
````

**_Note_**: By default, the crawler utilizes all available CPU cores on your system. 
For optimal performance, we recommend manually setting the number of processes using the `processes` parameter. 
A good rule of thumb is to allocate `one process per 200 Mbps of bandwidth`.
This can vary depending on core speed.

**_Note_**: The crawl above took ~7 hours using the entire `PublisherCollection` on a machine with 1000 Mbps connection, Core i9-13905H, 64GB Ram, Windows 11 and without printing the articles.
The estimated time can vary substantially depending on the publisher used and the available bandwidth.
Additionally, not all publishers are included in the `CC-NEWS` crawl (especially US based publishers).
For large corpus creation, one can also use the regular crawler by utilizing only sitemaps, which requires significantly less bandwidth.

````python
from fundus import PublisherCollection, Crawler, Sitemap

# initialize a crawler for us/uk based publishers and restrict to Sitemaps only
crawler = Crawler(PublisherCollection.us, PublisherCollection.uk, restrict_sources_to=[Sitemap])

# crawl 1 million articles and print
for article in crawler.crawl(max_articles=1000000):
  print(article)
````


## Tutorials

We provide **quick tutorials** to get you started with the library:

1. [**Tutorial 1: How to crawl news with Fundus**](docs/1_getting_started.md)
2. [**Tutorial 2: How to crawl articles from CC-NEWS**](docs/2_crawl_from_cc_news.md)
3. [**Tutorial 3: The Article Class**](docs/3_the_article_class.md)
4. [**Tutorial 4: How to filter articles**](docs/4_how_to_filter_articles.md)
5. [**Tutorial 5: Advanced topics**](docs/5_advanced_topics.md)
6. [**Tutorial 6: Logging**](docs/6_logging.md)

If you wish to contribute check out these tutorials:
1. [**How to contribute**](docs/how_to_contribute.md)
2. [**How to add a publisher**](docs/how_to_add_a_publisher.md)

## Currently Supported News Sources

You can find the publishers currently supported [**here**](/docs/supported_publishers.md).

Also: **Adding a new publisher is easy - consider contributing to the project!**

## Evaluation benchmark

Check out our evaluation [benchmark](https://github.com/dobbersc/fundus-evaluation).

| **Scraper** | **Precision**             | **Recall**                | **F1-Score**              |
|-------------|---------------------------|---------------------------|---------------------------|
| [Fundus](https://github.com/flairNLP/fundus)      | **99.89**<sub>±0.57</sub> | 96.75<sub>±12.75</sub>    | **97.69**<sub>±9.75</sub> |
| [Trafilatura](https://github.com/adbar/trafilatura) | 90.54<sub>±18.86</sub>    | 93.23<sub>±23.81</sub>    | 89.81<sub>±23.69</sub>    |
| [BTE](https://github.com/dobbersc/fundus-evaluation/blob/master/src/fundus_evaluation/scrapers/bte.py)         | 81.09<sub>±19.41</sub>    | **98.23**<sub>±8.61</sub> | 87.14<sub>±15.48</sub>    |
| [jusText](https://github.com/miso-belica/jusText)     | 86.51<sub>±18.92</sub>    | 90.23<sub>±20.61</sub>    | 86.96<sub>±19.76</sub>    |
| [news-please](https://github.com/fhamborg/news-please) | 92.26<sub>±12.40</sub>    | 86.38<sub>±27.59</sub>    | 85.81<sub>±23.29</sub>    |
| [BoilerNet](https://github.com/dobbersc/fundus-evaluation/tree/master/src/fundus_evaluation/scrapers/boilernet)   | 84.73<sub>±20.82</sub>    | 90.66<sub>±21.05</sub>    | 85.77<sub>±20.28</sub>    |
| [Boilerpipe](https://github.com/kohlschutter/boilerpipe)  | 82.89<sub>±20.65</sub>    | 82.11<sub>±29.99</sub>    | 79.90<sub>±25.86</sub>    |

## Cite

Please cite the following [paper](https://arxiv.org/abs/2403.15279) when using Fundus or building upon our work:

```bibtex
@misc{dallabetta2024fundus,
      title={Fundus: A Simple-to-Use News Scraper Optimized for High Quality Extractions}, 
      author={Max Dallabetta and Conrad Dobberstein and Adrian Breiding and Alan Akbik},
      year={2024},
      eprint={2403.15279},
      archivePrefix={arXiv},
      primaryClass={cs.CL}
}
```

## Contact

Please email your questions or comments to [**Max Dallabetta**](mailto:max.dallabetta@googlemail.com?subject=[GitHub]%20Fundus)

## Contributing

Thanks for your interest in contributing! There are many ways to get involved;
start with our [contributor guidelines](docs/how_to_contribute.md) and then
check these [open issues](https://github.com/flairNLP/fundus/issues) for specific tasks.

## License

[MIT](LICENSE)
