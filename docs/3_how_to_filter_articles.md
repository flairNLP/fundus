# How to filter articles

This tutorial shows you how to filter articles based on their attribute values, URLs, and news sources.

## Extraction filter

A specific article may not contain all attributes the parser is capable of extracting.
By default, Fundus drops all articles that aren't fully extracted to ensure data quality.
You may miss a lot of data potentially useful for your project.
To alter this behavior make use of the `extration_filter` parameter of the `crawl()` method.
You do so by either using the built-in `ExtractionFilter` `Requires` or writing a custom one.

Let's print some articles with at least a `body` and `title` set.

````python
from fundus import Crawler, PublisherCollection, Requires

crawler = Crawler(PublisherCollection.de)

for article in crawler.crawl(max_articles=2, only_complete=Requires("title", "body")):
    print(article)
````

**_NOTE:_** We recommend thinking about what kind of data is needed first and then running Fundus with a configured extraction filter afterward.

### Custom extraction filter

Writing custom extraction filters is supported and encouraged.
To do so you need to define a `Callable` satisfying the `ExtractionFilter` protocol which you can find [here](../src/fundus/scraping/filter.py).

Let's build a custom extraction filter that rejects all articles which do not contain the word string `usa`.

````python
from typing import Dict, Any

def topic_filter(extracted: Dict[str, Any]) -> bool:
    if topics := extracted.get("topics"):
        if "usa" in [topic.casefold() for topic in topics]:
            return False
    return True
````

and put it to work.

````python
from fundus import Crawler, PublisherCollection

crawler = Crawler(PublisherCollection.us)
for us_themed_article in crawler.crawl(only_complete=topic_filter):
    print(us_themed_article)
````

**_NOTE:_** Fundus' filters work inversely to Python's built-in filter.
A filter in Fundus describes what is filtered out and not what's kept.
If a filter returns True on a specific element the element will be dropped.

#### Some more extraction filter examples:

````python
# only select articles from the past seven days
def date_filter(extracted: Dict[str, Any]) -> bool:
    end_date = datetime.date.today() - datetime.timedelta(weeks=1)
    start_date = end_date - datetime.timedelta(weeks=1)
    if publishing_date := extracted.get("publishing_date"):
        return not (start_date <= publishing_date.date() <= end_date)
    return True

# only select articles which include at least one string from ["pollution", "climate crisis"] in the article body
def body_filter(extracted: Dict[str, Any]) -> bool:
    if body := extracted.get("body"):
        for word in ["pollution", "climate crisis"]:
            if word in str(body).casefold():
                return False
    return True
````

## URL filter

Fundus allows you to filter articles by URL both before and after the HTML is downloaded.
You do so by making use of the `url_filter` parameter of the `crawl()` method.
There is a built-in filter called `regex_filter` that filters out URLs based on regular expressions.

Let's crawl a bunch of articles with URLs not including the word `advertisement` or `podcast` and print their `resuestd_url`'s.

````python
from fundus import Crawler, PublisherCollection
from fundus.scraping.filter import regex_filter

crawler = Crawler(PublisherCollection.us)

for article in crawler.crawl(max_articles=5, url_filter=regex_filter("advertisement|podcast")):
    print(article.html.requested_url)
````

Often it's useful to select certain criteria rather than filtering them.
To do so use the `inverse` operator from `fundus.scraping.filter.py`.

Let's crawl a bunch of articles with URLs including the string `politic`.

````python
from fundus import Crawler, PublisherCollection
from fundus.scraping.filter import inverse, regex_filter

crawler = Crawler(PublisherCollection.us)

for article in crawler.crawl(max_articles=5, url_filter=inverse(regex_filter("politic"))):
    print(article.html.requested_url)
````

Which should print something like this:

````console
https://www.foxnews.com/politics/matt-gaetz-fisa-surveillance-citizens
https://www.thenation.com/article/politics/jim-jordan-chris-wray/
https://www.newyorker.com/podcast/political-scene/will-record-temperatures-finally-force-political-change
https://www.cnbc.com/2023/07/12/thai-elections-deep-generational-divides-belie-thailands-politics.html
https://www.reuters.com/business/autos-transportation/volkswagens-china-chief-welcomes-political-goal-germanys-beijing-strategy-2023-07-13/
````

**_NOTE:_** As with the `ExtractionFilter` you can also write custom URL filters satisfying the `URLFilter` protocol.

### Combine filters

Sometimes it is useful to combine filters of the same kind.
You can do so by using the `lor` (logic `or`) and `land` (logic `and`) operators from `fundus.scraping.filter.py`.

Let's combine both URL filters from the examples above and add a new condition.
Our goal is to get articles that include both strings 'politic' and 'trump' in their URL and don't include the strings 'podcast' or 'advertisement'.

````python
from fundus import Crawler, PublisherCollection
from fundus.scraping.filter import inverse, regex_filter, lor, land

crawler = Crawler(PublisherCollection.us)

filter1 = regex_filter("advertisement|podcast") # drop all URLs including the strings "advertisement" or "podcast"
filter2 = inverse(land(regex_filter("politic"), regex_filter("trump"))) # drop all URLs not including the strings "politic" and "trump"

for article in crawler.crawl(max_articles=10, url_filter=lor(filter1, filter2)):
    print(article.html.requested_url)
````

Which should print something like this:

````console
https://www.foxnews.com/politics/desantis-meet-donors-new-yorks-southampton-next-week-pitch-campaigns-long-game-trump
https://occupydemocrats.com/2023/06/25/the-grift-trump-shifting-political-contributions-from-his-campaign-to-defense-fund/
https://www.foxnews.com/politics/trump-slams-doj-not-backing-him-e-jean-carroll-case-repeats-claim-doesnt-know-her
https://www.foxnews.com/politics/ron-desantis-wont-consider-being-trumps-running-mate-says-hes-not-number-2
https://www.foxnews.com/politics/georgia-swears-grand-jury-hear-trump-2020-election-case
https://www.foxnews.com/politics/chris-christie-tim-scott-reach-donor-requirement-participate-first-gop-debate-trump-yet-commit
https://www.newyorker.com/news/the-political-scene/will-trumps-crimes-matter-on-the-campaign-trail
https://occupydemocrats.com/2023/02/22/exploitation-trump-slammed-for-politicizing-toxic-train-derailment-with-ohio-visit/
https://www.thegatewaypundit.com/2023/06/pres-trump-defends-punching-down-politics-says-its/
https://www.thegatewaypundit.com/2023/06/breaking-poll-trump-most-popular-politician-country-rfk/
````

**_NOTE:_** You can use the `combine`, `lor`, and `land` operators on `ExtractionFilter` as well.
Make sure to only use them on filters of the same kind.

## Filter sources

Fundus supports different sources for articles which are split into two categories:

1. Only recent articles: `RSSFeed`, `NewsMap` (recommended for continuous crawling jobs)
2. The whole site: `Sitemap` (recommended for one-time crawling)

**_NOTE:_** Sometimes the `Sitemap` provided by a specific publisher won't span the entire site.

You can preselect the source for your articles when initializing a new `Crawler`.
Let's initiate a crawler who only crawls from `NewsMaps`'s.

````python
from fundus import Crawler, PublisherCollection, NewsMap

crawler = Crawler(PublisherCollection.us, restrict_sources_to=[NewsMap])
````

**_NOTE:_** The `restrict_sources_to` parameter expects a list as value to specify multiple sources at once, e.g. `[RSSFeed, NewsMap]`

## Filter unique articles

The `crawl()` method supports functionality to filter out articles with URLs previously encountered in this run.
You can alter this behavior by setting the `only_unique` parameter.

In the [next section](4_how_to_search_for_publishers.md) we will show you how to search through publishers in the `PublisherCollection`.
