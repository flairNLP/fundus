# We Want You!

First of all: Thank you for thinking about making Fundus better.
We try to tackle news scraping with domain-specific parsers to focus on precise extraction.
To handle this massive workload, we depend on people like you to contribute.

# What is Fundus

Fundus aims to be a very lightweight but precise news-scraping library.
Easy to use while being able to precisely extract information from provided HTML.
At its core Fundus is a massive parser library.
Rather than automate the extraction layer, Fundus builds on handcrafted parsers.
In consequence, for Fundus to be able to parse a specific news domain, someone has to write a parser specific to this domain.
And there are a lot of domains.

# How to contribute

Before contributing to Fundus you should check if you have Fundus installed in `editable` mode and using dev-requirements.
If you haven't done this so far or aren't sure about you should

1. Clone the repository
2. Optional but recommended: Create a virtual environment (.venv) or conda environment
3. Navigate to the root of the repository
4. Run pip install -e .[dev]

## How to add a Publisher

Before contributing a parser, check the [**supported publishers**](supported_publishers.md) table if there is already support for your desired publisher.
In the following, we will walk you through an example implementation of the [*Los Angeles Times*](https://www.latimes.com/) covering the best practices for adding a news source.

### 1. Creating a Parser Stub

Take a look at the file structure in `fundus/publishers`.
Fundus uses the [**ALPHA-2**](https://www.iban.com/country-codes) codes specified in ISO3166 to sort publishers into directories by country of origin.
For example:

- `fundus/publishers/de/` for German publishers
- `fundus/publishers/us/` for US publishers
- ...

Now create an empty file in the corresponding country section using the publishers' name - or some kind of abbreviation - as the file name.
For the Los Angeles Times, the correct country section is `fundus/publishers/us/`, since they are a newspaper based in the United States, with a filename like `la_times.py` or `los_angeles_times.py`.
We will continue here with `la_times.py`.
In the newly created file, add an empty parser class inheriting from `ParserProxy` and a parser version `V1` subclassing `BaseParser`.

``` python
from fundus.parser import ParserProxy, BaseParser


class LATimesParser(ParserProxy):
    class V1(BaseParser):
        pass
```

Internally, the `ParserProxy` maps crawl dates to specific versions (`V1`, `V2`, etc.) subclassing `BaseParser`.
Since Fundus' parsers are written by hand and in most cases bound to the layout they were written for, Fundus takes the extra proxying step to address changes to the layout.

### 2. Creating a Publisher Specification

Add a new publisher specification for the publisher you want to cover.
The publisher specification links information about the publisher, sources where to get the HTML to parse from, and the corresponding parser to an object used by Fundus' `Crawler`.

You can add a new entry to the country-specific `PublisherEnum` in the `__init__.py` of the country section you want to contribute to, i.e. `fundus/publishers/<country_code>/__init__.py`.
For now, we only specify the publisher's name, domain, and parser.
We will cover sources in the next step.

For the Long Angeles Times, we add the following entry to `fundus/publishers/us/__init__.py`.

``` python
class US(PublisherEnum):
    LATimes = PublisherSpec(
        name="Los Angeles Times",
        domain="https://www.latimes.com/",
        parser=LATimesParser,
    )
```

If the country section for your publisher did not exist before step 1, please add the `PublisherEnum` to `src/library/collection/__init__.py'`.

### 2. Creating a Publisher Specification

Add a new publisher specification for the publisher you want to cover.
The publisher specification links information about the publisher, sources where to get the HTML to parse from, and the corresponding parser to an object used by Fundus' `Crawler`.

You can add a new entry to the country-specific `PublisherEnum` in the `__init__.py` of the country section you want to contribute to, i.e. `fundus/publishers/<country_code>/__init__.py`.
For now, we only specify the publisher's name, domain, and parser.
We will cover sources in the next step.

For the Long Angeles Times, we add the following entry to `fundus/publishers/us/__init__.py`.

``` python
class US(PublisherEnum):
    LATimes = PublisherSpec(
        name="Los Angeles Times",
        domain="https://www.latimes.com/",
        parser=LATimesParser,
    )
```

If the country section for your publisher did not exist before step 1, please add the `PublisherEnum` to `src/library/collection/__init__.py'`.

#### Adding Sources

For your newly added publisher to work we first need to specify where to find articles - in the form of HTML - to parse.
To do so Fundus utilizes access points provided by the publishers rather than using a generic approach like web spiders.
There are many different forms in which publishers allow you to reach their articles with the most popular being RSS feeds, APIs, or sitemaps.
Currently, Fundus supports RSS feeds and sitemaps by adding them as corresponding `URLSourece` to the `PublisherSpec` using the `source` parameter.

##### Different `URLSource` types

Fundus provides the following types of `URLSource` you can import from `fundus.scraping.html`.

1. `RSSFeed` - specifying RSS feeds
2. `Sitemap` - specifying sitemaps
3. `NewsMap` - specifying a special kind of sitemap displaying only recent articles

Fundus differentiates between different source types in order to provide the functionality to crawl only recent articles (`RSSFeed`, `NewsMap`) or an entire website (`Sitemap`).
We do so mainly for efficiency reasons.
Refer to [this](3_how_to_filter_articles.md) documentation on how to filter for different source types.

**_NOTE:_** Every added publisher should try to specify at least one `Sitemap` and one `RSSFeed` or `NewsMap` (preferred).
If your publisher provides a `NewsFeed`, there is no need to specify an `RSSFeed`.

##### How to specify a `URLSource`

To build a `URLSource` you have to set an entry point URL using the `url` parameter.

###### RSS feeds

Getting links for RSS feeds differs from publisher to publisher.
Most of the time you can find them through a quick browser search.
Building an `RSSFeed` looks like this:
````python
from fundus.scraping.html import RSSFeed
RSSFeed("https://theintercept.com/feed/?rss")
````

###### Sitemaps
 
Sitemaps are a collection of `<url>` tags, indicating links to articles with properties attached and following a normed schema.
A typical sitemap looks like this:
```
<urlset ... >
   <url>
      <loc>https://www.latimes.com/recipe/peach-frozen-yogurt</loc>
      <lastmod>2020-01-29</lastmod>
   </url>
   ...
```
Links to sitemaps can typically be found within - often at the end of - the `robots.txt` file provided by the publisher.
You can access this file by attaching `robots.txt` at the end of the publisher domain.
E.g. for the LA Times reach `https://www.latimes.com/robots.txt` through your preferred browser.
This will give you the following two sitemap links.

````
Sitemap: https://www.latimes.com/sitemap.xml
````

referring to a sitemap, and

````
Sitemap: https://www.latimes.com/news-sitemap.xml
````

pointing to a `NewsMap`, which is a special kind of sitemap.
To have a look at how to differentiate between those two, refer to [this](#how-to-differentiate-between-sitemap-and-newsmap) section.

**_NOTE:_** There is a known issue with Firefox not displaying XML properly.
You can find a plugin to resolve this issue [here](https://addons.mozilla.org/de/firefox/addon/pretty-xml/)

Most `Sitemaps`, and sometimes `NewsMaps` as well, will be index maps.
E.g. accessing `https://www.latimes.com/news-sitemap.xml` will give you something like this:
```
<sitemapindex ... >
   <sitemap>
      <loc>https://www.latimes.com/news-sitemap-content.xml</loc>
      <lastmod>2023-08-02T07:10-04:00</lastmod>
   </sitemap>
   ...
</sitemapindex>
```
The `<sitemap>`, and especially the `<sitemapindex>` tag, indicates that this is, in fact, an index map pointing to other sitemaps rather than articles.
To address this, `Sitemap` and `NewsMap` will step through the given sitemap recursively by default.
You can alter this behavior or reverse the order in which sitemaps are processed with the `recursive` respectively `reverse` parameters.

**_NOTE:_** If you wonder why you should reverse your sources from time to time, `URLSource`'s should, if possible, yield URLs in descending order by publishing date.

Now building a new `URLSource` for a `NewsMap` covering the LA Times looks like this:
````python
from fundus.scraping.html import NewsMap
NewsMap("https://www.latimes.com/news-sitemap.xml", reverse=True)
````

##### How to differentiate between `Sitemap` and `NewsMap`

Fundus differentiates between two types of sitemaps: 
Those that almost or actually span the entire site (`Sitemap`) and those that only reference recent articles (`NewsMap`), often called [**Google News Maps**](https://support.google.com/news/publisher-center/answer/9607107?hl=en&ref_topic=9606468).
You can check if a sitemap is a news map by:
1. Checking the file name: 
   Often there is a string like `news` included.
   While this is a very simple method this can be unreliable.
2. Checking the namespace:
   Typically there is a namespace `news` defined within a news map using the `xmlns:news` attribute of the `<urlset>` tag.
   E.g. `<urlset ... xmlns:news="http://www.google.com/schemas/sitemap-news/0.9" ... >`
   **_NOTE:_** This can only be found within the actual sitemap and not an index map.

The line we are looking for is `xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"`.
Here, the prefix `news` is bound to the namespace `http://www.google.com/schemas/sitemap-news/0.9`.
This indicates the sitemap is a Google News Sitemap.
Thus `https://www.latimes.com/news-sitemap.xml` is a Google News Index Map.

#### Finishing the Publisher Specification

1. Sometimes sitemaps can include a lot of noise like maps pointing to a collection of tags or authors, etc.
   You can use the `sitemap_filter` parameter of `Sitemap` or `NewsMap` to prefilter these based on a regular expression.
2. If your publisher requires to use custom request headers to work properly you can alter it by using the `request_header` parameter.
   The default is: `{"user_agent": "fundus"}`.
3. If you want to block URLs for the entire publisher use the `url_filter` parameter.

Bringing all of this section together our specification for the LA Times looks like this.

``` python
class US(PublisherEnum):
    LATimes = PublisherSpec(
        name="Los Angeles Times",
        domain="https://www.latimes.com/",
        sources=[Sitemap("https://www.latimes.com/sitemap.xml"), 
                 NewsMap("https://www.latimes.com/news-sitemap.xml")],
        parser=LATimesParser,
    )
```

### 4. Validating the Current Implementation Progress

Now validate your implementation progress by crawling some example articles from your publisher.
The following script fits the Los Angeles Times and is adaptable by changing the publisher variable accordingly.

``` python
from fundus import PublisherCollection, Crawler

# Change to:
# PublisherCollection.<country_section>.<publisher_specification>
publisher = PublisherCollection.us.LosAngelesTimes

crawler = Crawler(publisher)

for article in crawler.crawl(max_articles=2):
    print(article)
```

If everything has been implemented correctly, the script should output text articles like the following.

``` console
Fundus-Article:
- Title: "--missing title--"
- Text:  "--missing plaintext--"
- URL:    https://www.latimes.com/sports/story/2023-06-26/100-years-los-angeles-coliseum-historical-events
- From:   Los Angeles Times
Fundus-Article:
- Title: "--missing title--"
- Text:  "--missing plaintext--"
- URL:    https://www.latimes.com/sports/sparks/story/2023-06-25/los-angeles-sparks-dallas-wings-wnba-game-analysis
- From:   Los Angeles Times
```

Since we didn't add any specific implementation to the parser yet, most entries are empty.

### 5. Implementing the Parser

Bring your parser to life and fill it with attributes to parse.

One important caveat to consider is the type of content on a particular page.
For example, various news outlets use live tickers, sites that display a podcast, or hub sites which are not articles but link to other pages.
At the current state of this library, you do not need to worry about sites that are not articles.
Your code should be able to extract the desired attributes from most pages of the publisher you are adding.
Sites that do not contain the desired attributes will be filtered by the library on their own in a later stage of the pipeline.

You can add attributes by decorating the methods of your parser with the `@attribute` decorator.
Attributes are expected to have a return value precisely specified in the [attribute guidelines](attribute_guidelines.md).

For example, if we want our parser to extract article titles, we take the [attribute guidelines](attribute_guidelines.md) and look for a defined attribute that matches our expectations.
In the guidelines, we find an attribute called `title`, which exactly describes what we want to extract and the expected return type.
You must stick to the specified return types since they are enforced in our unit tests.
You're free to experiment locally, but you won't be able to contribute to the repository when your PR isn't compliant with the guidelines.

**_NOTE:_**
If you want to add an attribute not listed in the guidelines set the `validate` parameter of the attribute decorator to `False` like this:

``` python
@attribute(validate=False)
def unsupported_attribute(self):
   ...
```

Attributes with validate set to `False` will not be validated through unit tests.
If you have problems implementing your desired publisher feel free to ask questions in the [**issue**](https://github.com/flairNLP/fundus/issues) tab.

Now that we have our attribute name, we add it to the parser by defining a method called `title` and declaring it as an attribute with the `@attribute` decorator.

``` python
class LATimesParser(ParserProxy):
    class V1(BaseParser):

        @attribute
        def title(self) -> Optional[str]:
            return "This is a title"
```

Now let's print our newly added titles.

``` python
for article in crawler.crawl(max_articles=2):
    print(article.title)
```

Which should print the following output

```console
This is a title
This is a title 
```

Fundus will automatically add your decorated attributes as instance attributes to the `article` object during parsing.
Attributes defined in the [attribute guidelines](attribute_guidelines.md) are additionally defined as `dataclasses.fields`.

#### Extracting Attributes from Precomputed

To let your parser extract useful information rather than placeholders, one way is to use the `ld` and `meta` attributes of the `Article`.
These attributes are automatically extracted when present in the HTML and are accessible during parsing time within your parser's attributes.
Often useful information about an article like the `title`, `author` or `topics` can be found in these two objects.
You can access them inside your parser class via the `precomputed` attribute of `BaseParser`, which holds a `dataclass` of type `Precomputed`.
This object contains meta information about the article you're currently parsing.

``` python
@dataclass
class Precomputed:
    html: str
    doc: lxml.html.HtmlElement
    meta: Dict[str, str]
    ld: LinkedData
    cache: Dict[str, Any]
```

In the following table, you can find a short description of the fields of the `precomputed` attribute.

| Precomputed Attribute | Description                                                                                                                                            |
|-----------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| html                  | The original fetched HTML.                                                                                                                             |
| doc                   | The root node of an `lxml.html.Etree` spanning the fetched html.                                                                                       |
| meta                  | The article's meta-information extracted from `<meta>` tags.                                                                                           |
| ld                    | The linked data extracted from the HTML's [`ld+json`](https://json-ld.org/)                                                                            |
| cache                 | A cache specific to the currently parsed site which can be used to share objects between attributes. Share objects with the `BaseParser.share` method. |

For example, to extract the title for an article in the Los Angeles Times, we can access the `og:title` through the `meta` precomputed attribute.

``` python
@attribute
def title(self) -> Optional[str]:
   # Use the `get` function to retrieve data from the `meta` precomputed attribute
   return self.precomputed.meta.get("og:title")
```

#### Extracting Attributes with XPath and CSS-Select

Sometimes you have to get information directly from the DOM of the HTML (in most cases the article text).
To do so we suggest using [**lxml**](https://lxml.de/) and selectors like [`XPath`](https://lxml.de/xpathxslt.html) or [`CSSSelect`](https://lxml.de/cssselect.html).
You can use both selectors on the `doc` attribute of `Precomputed`.
If you use a selector in any of your attributes (which will be most likely the case when extracting the actual article text) you should precompute the selector as a class variable using the `XPath` respectively `CSSSelector` classes of lxml.

**_NOTE:_** There are many utility functions defined at `fundus/parser/utility.py` to aid you when implementing parser attributes.
Make sure to check out other parsers and refer to the attribute guidelines on how to implement specific attributes. 
We highly recommend using the utility functions, especially when parsing the `ArticleBody`.

#### Finishing the Parser

Bringing all the above together the Los Angeles Times now looks like this.

```python
import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class LATimesParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("div[data-element*=story-body] > p")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def publishing_date(self) -> datetime.datetime:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")
```

Now, execute the example script from step 4 to validate your implementation.
If the attributes are implemented correctly, they appear in the printout accordingly.

```console
Fundus-Article:
- Title: "One hundred years at the Coliseum: Much more than a sports venue"
- Text:  "Construction for the Los Angeles Coliseum was completed on May 1, 1923. Capacity
          at the time: 75,000. The stadium was designed by architects John [...]"
- URL:    https://www.latimes.com/sports/story/2023-06-26/100-years-los-angeles-coliseum-historical-events
- From:   Los Angeles Times (2023-06-26 12:00)
Fundus-Article:
- Title: "Sparks back at .500: Five things to know about the team after win Sunday"
- Text:  "Finally, the home crowd at Crypto.com Arena had something to cheer about.  After
          dropping the first three games of their longest homestand of the [...]"
- URL:    https://www.latimes.com/sports/sparks/story/2023-06-25/los-angeles-sparks-dallas-wings-wnba-game-analysis
- From:   Los Angeles Times (2023-06-25 21:30)
```

### 6. Generate unit tests

To finish your newly added publisher you should add unit tests for the parser.
We recommend you do this with the provided [**script**](../scripts/generate_parser_test_files.py).

To get started with this script, you may read the provided manual:

````shell
python -m scripts.generate_parser_test_files -h
````

Then in most cases it should be enough to simply run

````shell
python -m scripts.generate_parser_test_files -p <your_publisher_class>
````

with <your_publisher_class> being the class name of the `PublisherEnum` your working on.

In our case, we would run:

````shell
python -m scripts.generate_parser_test_files -p LATimes
````

to generate a unit test for our parser.

Now to test your newly added publisher you should run pytest with the following command:

````shell
pytest
````

### 7. Opening a Pull Request

1. Make sure you tested your parser using `pytest`.
2. Run `black src`, `isort src`, and `mypy src` with no errors.
3. Push and open a new PR
4. Congratulation and thank you very much.
