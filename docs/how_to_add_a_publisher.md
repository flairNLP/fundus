# Table of Contents

* [How to add a Publisher](#how-to-add-a-publisher)
  * [1. Creating a Parser Stub](#1-creating-a-parser-stub)
  * [2. Creating a Publisher Specification](#2-creating-a-publisher-specification)
    * [Adding Sources](#adding-sources)
      * [Different `URLSource` types](#different-urlsource-types)
      * [How to specify a `URLSource`](#how-to-specify-a-urlsource)
        * [RSS feeds](#rss-feeds)
        * [Sitemaps](#sitemaps)
      * [How to differentiate between `Sitemap` and `NewsMap`](#how-to-differentiate-between-sitemap-and-newsmap)
    * [Finishing the Publisher Specification](#finishing-the-publisher-specification)
  * [4. Validating the Current Implementation Progress](#4-validating-the-current-implementation-progress)
  * [5. Implementing the Parser](#5-implementing-the-parser)
    * [Extracting Attributes from Precomputed](#extracting-attributes-from-precomputed)
    * [Extracting Attributes with XPath and CSS-Select](#extracting-attributes-with-xpath-and-css-select)
      * [Working with `lxml`](#working-with-lxml)
      * [CSS-Select](#css-select)
      * [XPath](#xpath)
    * [Finishing the Parser](#finishing-the-parser)
  * [6. Generate unit tests](#6-generate-unit-tests)
  * [7. Opening a Pull Request](#7-opening-a-pull-request)

# How to add a Publisher

Before contributing a publisher make sure you setup Fundus correctly alongside [this](how_to_contribute.md#setup-fundus) steps.
Then check the [**supported publishers**](supported_publishers.md) table if there is already support for your desired publisher.
In the following, we will walk you through an example implementation of the [*Los Angeles Times*](https://www.latimes.com/) covering the best practices for adding a new publisher.

## 1. Creating a Parser Stub

Take a look at the file structure in `fundus/publishers`.
Fundus uses the [**ALPHA-2**](https://www.iban.com/country-codes) codes specified in ISO3166 to sort publishers into directories by country of origin.
For example:

- `fundus/publishers/de/` for German publishers
- `fundus/publishers/us/` for US publishers
- ...

Now create an empty file in the corresponding country section using the publishers' name or some abbreviation as the file name.
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
Since Fundus' parsers are handcrafted and usually tied to specific layouts, this proxying step helps address changes to the layout.

## 2. Creating a Publisher Specification

Next, add a new publisher specification for the publisher you want to cover.
The publisher specification links information about the publisher, sources from where to get the HTML to parse, and the corresponding parser used by Fundus' `Crawler`.

You can add a new entry to the country-specific `PublisherEnum` in the `__init__.py` of the country section you want to contribute to, i.e. `fundus/publishers/<country_code>/__init__.py`.
For now, we only specify the publisher's name, domain, and parser.
We will cover sources in the next step.

For the Los Angeles Times (LA Times), we add the following entry to `fundus/publishers/us/__init__.py`.

``` python
class US(PublisherEnum):
    LATimes = PublisherSpec(
        name="Los Angeles Times",
        domain="https://www.latimes.com/",
        parser=LATimesParser,
    )
```

If the country section for your publisher did not exist before step 1, please add the `PublisherEnum` to `src/library/collection/__init__.py'`.

### Adding Sources

For your newly added publisher to work you first need to specify where to find articles - in the form of HTML - to parse.
Fundus adopts a unique approach by utilizing access points provided by the publishers, rather than resorting to generic web spiders.
Publishers offer various methods to access their articles, with the most common being RSS feeds, APIs, or sitemaps. 
Presently, Fundus supports RSS feeds and sitemaps by adding them as corresponding `URLSource` using the `source` parameter of `PublisherSpec`.

#### Different `URLSource` types

Fundus provides the following types of `URLSource`, which you can import from `fundus.scraping.html`.

1. `RSSFeed` - specifying RSS feeds
2. `Sitemap` - specifying sitemaps
3. `NewsMap` - specifying a special kind of sitemap displaying only recent articles

Fundus distinguishes between these source types to facilitate crawling only recent articles (`RSSFeed`, `NewsMap`) or an entire website (`Sitemap`).
This differentiation is mainly for efficiency reasons.
Refer to [this](3_how_to_filter_articles.md#filter-sources) documentation on how to filter for different source types.

**_NOTE:_** When adding a new publisher, it is recommended to specify at least one `Sitemap` and one `RSSFeed` or `NewsMap` (preferred).
If your publisher provides a `NewsFeed`, there is no need to specify an `RSSFeed`.

#### How to specify a `URLSource`

To instantiate an object inheriting from URLSource like `RSSFeed` or `Sitemap`, you first need to find a link to the corresponding feed or sitemap and then set it as the entry point using the `url` parameter of `URLSource`.

##### RSS feeds

Getting links for RSS feeds can vary from publisher to publisher.
Most of the time, you can find them through a quick browser search.
Building an `RSSFeed` looks like this:
````python
from fundus.scraping.html import RSSFeed
RSSFeed("https://theintercept.com/feed/?rss")
````

##### Sitemaps
 
Sitemaps consist of a collection of `<url>` tags, indicating links to articles with properties attached, following a standardized schema.
A typical sitemap looks like this:

```console
<urlset ... >
   <url>
      <loc>https://www.latimes.com/recipe/peach-frozen-yogurt</loc>
      <lastmod>2020-01-29</lastmod>
   </url>
   ...
```

**_NOTE:_** There is a known issue with Firefox not displaying XML properly.
You can find a plugin to resolve this issue [here](https://addons.mozilla.org/de/firefox/addon/pretty-xml/)

Links to sitemaps are typically found within the `robots.txt` file provided by the publisher, often located at the end of it.
To access this file, append `robots.txt` at the end of the publisher's domain.
For example, to access the LA Times' `robots.txt`, use https://www.latimes.com/robots.txt in your preferred browser.
 This will give you the following two sitemap links:

```console
Sitemap: https://www.latimes.com/sitemap.xml
Sitemap: https://www.latimes.com/news-sitemap.xml
````

The former refers to a regular sitemap, and the latter points to a NewsMap, which is a special kind of sitemap.
To have a look at how to differentiate between those two, refer to [this](#how-to-differentiate-between-sitemap-and-newsmap) section.

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

#### How to differentiate between `Sitemap` and `NewsMap`

Fundus differentiates between two types of sitemaps: 
Those that almost or actually span the entire site (`Sitemap`) and those that only reference recent articles (`NewsMap`), often called [**Google News Maps**](https://support.google.com/news/publisher-center/answer/9607107?hl=en&ref_topic=9606468).
You can check if a sitemap is a news map by:
1. Checking the file name: 
   Often there is a string like `news` included.
   While this is a very simple method this can be unreliable.
2. Checking the namespace:
   Typically there is a namespace `news` defined within a news map using the `xmlns:news` attribute of the `<urlset>` tag.
   E.g. `<urlset ... xmlns:news="http://www.google.com/schemas/sitemap-news/0.9" ... >`<br>
   **_NOTE:_** This can only be found within the actual sitemap and not the index map.

### Finishing the Publisher Specification

1. Sometimes sitemaps can include a lot of noise like maps pointing to a collection of tags or authors, etc.
   You can use the `sitemap_filter` parameter of `Sitemap` or `NewsMap` to prefilter these based on a regular expression.
   E.g. 
   ```` python
   Sitemap("https://apnews.com/sitemap.xml", sitemap_filter=regex_filter("apnews.com/hub/|apnews.com/video/"))
   ````
   Will filter out all URLs encountered within the processing of the `Sitemap` object including either the string `apnews.com/hub/` or `apnews.com/video/`.  
2. If your publisher requires to use custom request headers to work properly you can alter it by using the `request_header` parameter of `PublisherSpec`.
   The default is: `{"user_agent": "Fundus"}`.
3. If you want to block URLs for the entire publisher use the `url_filter` parameter of `PublisherSpec`.

Now, let's put it all together to specify the LA Times as a new publisher in Fundus:

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

## 4. Validating the Current Implementation Progress

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

## 5. Implementing the Parser

Now bring your parser to life and define the attributes you want to extract.

One important caveat to consider is the type of content on a particular page.
Some news outlets feature live tickers, displaying podcasts, or hub sites that link to other pages but are not articles themselves.
At this stage, there's no need to concern yourself with handling non-article pages. 
our parser should concentrate on extracting desired attributes from most pages that can be classified as articles.
Pages lacking the desired attributes will be filtered out by the library during a later phase of the processing pipeline.

You can add attributes by decorating the methods of your parser with the `@attribute` decorator.
The expected return value for each attribute must precisely match the specifications outlined in the [attribute guidelines](attribute_guidelines.md).

For instance, if you want to extract article titles, first refer to the [attribute guidelines](attribute_guidelines.md) and identify an attribute that aligns with your objective.
There you can locate an attribute named `title`, which precisely corresponds to what you aim to extract, along with its expected return type.
It is essential to adhere to the specified return types, as they are enforced through our unit tests.
While you're welcome to experiment locally, contributions to the repository won't be accepted if your pull request deviates from the guidelines.

**_NOTE:_**
Should you wish to add an attribute not covered in the guidelines, set the `validate` parameter of the attribute decorator to `False`, like this:

``` python
@attribute(validate=False)
def unsupported_attribute(self):
   ...
```

Attributes marked with `validate=False` will not be validated through unit tests.

Now, once we have identified the attribute we want to extract, we add it to the parser by defining a method using the associated name, in our case `title`, and marking it as an attribute using the `@attribute` decorator.

``` python
class LATimesParser(ParserProxy):
    class V1(BaseParser):

        @attribute
        def title(self) -> Optional[str]:
            return "This is a title"
```

To see the results of our newly added titles, we can use the following code:

``` python
for article in crawler.crawl(max_articles=2):
    print(article.title)
```

This should print the following output:

```console
This is a title
This is a title 
```

Fundus will automatically add your decorated attributes as instance attributes to the `article` object during parsing.
Additionally, attributes defined in the attribute guidelines are explicitly defined as `dataclasses.fields`.

### Extracting Attributes from Precomputed

One way to extract useful information from articles rather than placeholders is to utilize the `ld` and `meta` attributes of the `Article`.
These attributes are automatically extracted when they are present in the currently parsed HTML.
Often, valuable information about an article, such as the `title`, `author`, or `topics`, can be found in these two objects.
To access them during parsing, you can use the `precomputed` attribute of `BaseParser`, which references a `dataclass` of type `Precomputed`.
This object contains meta-information about the article you're currently parsing.

``` python
@dataclass
class Precomputed:
    html: str
    doc: lxml.html.HtmlElement
    meta: Dict[str, str]
    ld: LinkedData
    cache: Dict[str, Any]
```

Here is a brief description of the fields of `Precomputed`.

| Precomputed Attribute | Description                                                                                                                                             |
|-----------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| html                  | The original fetched HTML.                                                                                                                              |
| doc                   | The root node of an `lxml.html.Etree` spanning the fetched html.                                                                                        |
| meta                  | The article's meta-information extracted from `<meta>` tags.                                                                                            |
| ld                    | The linked data extracted from the HTML's [`ld+json`](https://json-ld.org/)                                                                             |
| cache                 | A cache specific to the currently parsed site, which can be used to share objects between attributes. Share objects with the `BaseParser.share` method. |

For instance, to extract the title for an article in the Los Angeles Times, we can access the `og:title` through the attribute `meta` of `Precomputed`.

``` python
@attribute
def title(self) -> Optional[str]:
   # Use the `get` function to retrieve data from the `meta` precomputed attribute
   return self.precomputed.meta.get("og:title")
```

### Extracting Attributes with XPath and CSS-Select

When parsing the `ArticleBody`, or the desired information cannot be extracted from the `ld` or `meta` attributes, you need to directly obtain information from the [Document Object Model](https://en.wikipedia.org/wiki/Document_Object_Model) (DOM) of the HTML/XML.
The DOM serves as an interface representing the underlying HTML or XML file as a tree structure, where each element (tag) of the file functions as a node in the tree.
To select or search respectively for the information you need you can access these nodes using selectors like CSS-Select or XPath.
Fundus relies on the Python package `lxml` and its selector implementation.

#### Working with `lxml`

Consider the following HTML example.

````html
<html lang="de">
    <head>
        <meta charset="utf-8">
        <title>...</title>
    </head>
    <body>
        <h2>This is a heading.</h2>
        <p>This is a paragraph inside the body.</p>
        <p class="A">This is a paragraph with a class.</p>
        <div>
            <p>This is a paragraph within a div</p>    
        </div>
        <div class="B">
            <p>This is a paragraph within a div of class B</p>    
        </div>
        <p additional-attribute="not allowed">This is a paragraph with a weird attribute</p>  
    </body>
</html>
````

To work with `lxml`  selectors, the initial step involves constructing an `Etree`, which represents the DOM of the HTML.
This is achieved as follows:

```` python
root = lxml.html.document_fromstring(html)
````

This will return an object of type `lxml.html.HtmlElement` representing the root node of the DOM tree.
Within the Fundus parser, the DOM tree is already generated for each article, and the root node can be accessed using the `doc` parameter of `Precomputed`.
Next we will show you how to specify search conditions in the form of selectors and use them on the tree.

#### CSS-Select

CSS-Select is generally a simpler, but less comprehensive, selector compared to XPath.
In most instances, it's advisable to use CSS-Select and resort to XPath only when necessary.
To define your selector we recommend using [this](https://www.w3schools.com/cssref/css_selectors.php) reference.

Here's an example of creating a selector to target all `<p>` tags within the tree and extracting their text content using `text_content()`:
```` python
from lxml.cssselect import CSSSelector

selector = CSSSelector("p")
nodes = selector(root)
for node in nodes:
    print(node.text_content())
````

This should print the following lines:

````console
This is a paragraph inside the body.
This is a paragraph with a class.
This is a paragraph within a div
This is a paragraph within a div of class B
This is a paragraph with a weird attribute
````

**_NOTE:_** The nodes are returned in depth-first pre-order.

Similarly, you can select based on the `class` attribute of a tag.
For instance, selecting all  `<p>` tags with class `A` looks like this.

```` python
selector = CSSSelector("p.A")
````

Which will print:

````console
This is a paragraph with a class.
````

Often you need to select tags depending on their parents.
To illustrate, let's select all `<p>` tags that have a `<div>` tag as their parent.

```` python
selector = CSSSelector("div > p")
````

Output:

````console
This is a paragraph within a div
This is a paragraph within a div of class B
````

Combining these techniques, you can select all  `<p>` tags that have a parent `<div>` with class `B`.

```` python
selector = CSSSelector("div.B > p")
````

Output:

````console
This is a paragraph within a div of class B
````

Selectors can also target nodes with specific attribute values, even if those attributes are not standard in the HTML specification:

```` python
selector = CSSSelector("p[additional-attribute='not allowed']")
````

Output:

````console
This is a paragraph with a weird attribute
````

**_NOTE:_** It's also possible to select solely by the existence of an attribute by omitting the equality.
Sticking to the above example you can simply use `CSSSelector("p[additional-attribute]")` instead.


#### XPath

Given the complexity of XPath compared to CSS-Select, we refrain from providing an extensive tutorial here.
Instead, we recommend referring to [this](https://devhints.io/xpath) documentation for a translation table and a concise overview of XPath functionalities beyond CSS-Select.

**_NOTE:_** Although it's possible to select nodes using the built-in methods of  `lxml.html.HtmlElement`, it's recommended to use the dedicated selectors [`CSSSelect`](https://lxml.de/cssselect.html) and [`XPath`](https://lxml.de/xpathxslt.html), as demonstrated in the above examples.

**_NOTE:_** The `fundus/parser/utility.py` module includes several utility functions that can assist you in implementing parser attributes.
Make sure to examine other parsers and consult the [attribute guidelines](attribute_guidelines.md) for specifics on attribute implementation. 
We strongly encourage utilizing these utility functions, especially when parsing the `ArticleBody`.

### Finishing the Parser

Bringing all the above together, the Los Angeles Times now looks like this.

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

## 6. Generate unit tests

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

## 7. Opening a Pull Request

1. Make sure you tested your parser using `pytest`.
2. Run `black src`, `isort src`, and `mypy src` with no errors.
3. Push and open a new PR
4. Congratulation and thank you very much.