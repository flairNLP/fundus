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

[Quick Start](#quick-start) | [Tutorials](#tutorials) | [News Sources](/docs/supported_publishers.md) | [Paper](https://aclanthology.org/2024.acl-demos.29/)

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
Fundus-Article including 1 image(s):
- Title: "Feinstein's Return Not Enough for Confirmation of Controversial New [...]"
- Text:  "89-year-old California senator arrived hour late to Judiciary Committee hearing
          to advance President Biden's stalled nominations  Democrats [...]"
- URL:    https://freebeacon.com/politics/feinsteins-return-not-enough-for-confirmation-of-controversial-new-hampshire-judicial-nominee/
- From:   The Washington Free Beacon (2023-05-11 18:41)

Fundus-Article including 3 image(s):
- Title: "Northwestern student government freezes College Republicans funding over [...]"
- Text:  "Student government at Northwestern University in Illinois "indefinitely" froze
          the funds of the university's chapter of College Republicans [...]"
- URL:    https://www.foxnews.com/us/northwestern-student-government-freezes-college-republicans-funding-poster-critical-lgbtq-community
- From:   Fox News (2023-05-09 14:37)
```

This printout tells you that you successfully crawled two articles!

For each article, the printout details:
- the number of images included in the article
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


## Example 4: Crawl some images

By default, Fundus tries to parse the images included in every crawled article.
Let's crawl an article and print out the images for some more details.

```python
from fundus import PublisherCollection, Crawler

# initialize the crawler for The LA Times
crawler = Crawler(PublisherCollection.us.LATimes)

# crawl 1 article and print the images
for article in crawler.crawl(max_articles=1):
    for image in article.images:
        print(image)
```

For [this article](https://www.latimes.com/sports/lakers/story/2024-12-13/lakers-lebron-james-away-from-team-timberwolves) you will get the following output:

```console
Fundus-Article Cover-Image:
-URL:			 'https://ca-times.brightspotcdn.com/dims4/default/41c9bc4/2147483647/strip/true/crop/4598x3065+0+0/resize/1200x800!/format/webp/quality/75/?url=https%3A%2F%2Fcalifornia-times-brightspot.s3.amazonaws.com%2F77%2Feb%2F7fed2d3942fd97b0f7325e7060cf%2Flakers-timberwolves-basketball-33765.jpg'
-Description:	         'Minnesota Timberwolves forward Julius Randle (30) works toward the basket.'
-Caption:		 'Minnesota Timberwolves forward Julius Randle, left, controls the ball in front of Lakers forward Anthony Davis during the first half of the Lakers’ 97-87 loss Friday.'
-Authors:		 ['Abbie Parr / Associated Press']
-Versions:		 [320x213, 568x379, 768x512, 1024x683, 1200x800]

Fundus-Article Image:
-URL:			 'https://ca-times.brightspotcdn.com/dims4/default/9a22715/2147483647/strip/true/crop/4706x3137+0+0/resize/1200x800!/format/webp/quality/75/?url=https%3A%2F%2Fcalifornia-times-brightspot.s3.amazonaws.com%2Ff7%2F52%2Fdcd6b263480ab579ac583a4fdbbf%2Flakers-timberwolves-basketball-48004.jpg'
-Description:	         'Lakers coach JJ Redick talks with forward Anthony Davis during a loss to the Timberwolves.'
-Caption:		 'Lakers coach JJ Redick, right, talks with forward Anthony Davis during the first half of a 97-87 loss to the Timberwolves on Friday night.'
-Authors:		 ['Abbie Parr / Associated Press']
-Versions:		 [320x213, 568x379, 768x512, 1024x683, 1200x800]

Fundus-Article Image:
-URL:			 'https://ca-times.brightspotcdn.com/dims4/default/580bae4/2147483647/strip/true/crop/5093x3470+0+0/resize/1200x818!/format/webp/quality/75/?url=https%3A%2F%2Fcalifornia-times-brightspot.s3.amazonaws.com%2F3b%2Fdf%2F64c0198b4c2fb2b5824aaccb64b7%2F1486148-sp-nba-lakers-trailblazers-25-gmf.jpg'
-Description:	         'Lakers star LeBron James sits in street clothes on the bench next to his son, Bronny James.'
-Caption:		 'Lakers star LeBron James sits in street clothes on the bench next to his son, Bronny James, during a win over Portland at Crypto.com Arena on Dec. 8.'
-Authors:		 ['Gina Ferazzi / Los Angeles Times']
-Versions:		 [320x218, 568x387, 768x524, 1024x698, 1200x818]
```

For each image, the printout details:
- The cover image designation (if applicable).
- The URL for the highest-resolution version of the image.
- A description of the image.
- The image's caption.
- The name of the copyright holder.
- A list of all available versions of the image.


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

## Evaluation Benchmark

Check out our evaluation [benchmark](https://github.com/dobbersc/fundus-evaluation).

The following table summarizes the overall performance of Fundus and evaluated scrapers in terms of averaged ROUGE-LSum precision, recall and F1-score and their standard deviation. The table is sorted in descending order over the F1-score:

| **Scraper**                                                                                                     | **Precision**             | **Recall**                | **F1-Score**              | **Version** |
|-----------------------------------------------------------------------------------------------------------------|:--------------------------|---------------------------|---------------------------|-------------|
| [Fundus](https://github.com/flairNLP/fundus)                                                                    | **99.89**<sub>±0.57</sub> | 96.75<sub>±12.75</sub>    | **97.69**<sub>±9.75</sub> | 0.4.1       |
| [Trafilatura](https://github.com/adbar/trafilatura)                                                             | 93.91<sub>±12.89</sub>    | 96.85<sub>±15.69</sub>    | 93.62<sub>±16.73</sub>    | 1.12.0      |
| [news-please](https://github.com/fhamborg/news-please)                                                          | 97.95<sub>±10.08</sub>    | 91.89<sub>±16.15</sub>    | 93.39<sub>±14.52</sub>    | 1.6.13      |
| [BTE](https://github.com/dobbersc/fundus-evaluation/blob/master/src/fundus_evaluation/scrapers/bte.py)          | 81.09<sub>±19.41</sub>    | **98.23**<sub>±8.61</sub> | 87.14<sub>±15.48</sub>    | /           |
| [jusText](https://github.com/miso-belica/jusText)                                                               | 86.51<sub>±18.92</sub>    | 90.23<sub>±20.61</sub>    | 86.96<sub>±19.76</sub>    | 3.0.1       |
| [BoilerNet](https://github.com/dobbersc/fundus-evaluation/tree/master/src/fundus_evaluation/scrapers/boilernet) | 85.96<sub>±18.55</sub>    | 91.21<sub>±19.15</sub>    | 86.52<sub>±18.03</sub>    | /           |
| [Boilerpipe](https://github.com/kohlschutter/boilerpipe)                                                        | 82.89<sub>±20.65</sub>    | 82.11<sub>±29.99</sub>    | 79.90<sub>±25.86</sub>    | 1.3.0       |

## Cite

Please cite the following [paper](https://aclanthology.org/2024.acl-demos.29/) when using Fundus or building upon our work:

```bibtex
@inproceedings{dallabetta-etal-2024-fundus,
    title = "Fundus: A Simple-to-Use News Scraper Optimized for High Quality Extractions",
    author = "Dallabetta, Max  and
      Dobberstein, Conrad  and
      Breiding, Adrian  and
      Akbik, Alan",
    editor = "Cao, Yixin  and
      Feng, Yang  and
      Xiong, Deyi",
    booktitle = "Proceedings of the 62nd Annual Meeting of the Association for Computational Linguistics (Volume 3: System Demonstrations)",
    month = aug,
    year = "2024",
    address = "Bangkok, Thailand",
    publisher = "Association for Computational Linguistics",
    url = "https://aclanthology.org/2024.acl-demos.29",
    pages = "305--314",
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
