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
    * [Extract the ArticleBody](#extract-the-articlebody)
    * [Checking the free_access attribute](#checking-the-free_access-attribute)
    * [Finishing the Parser](#finishing-the-parser)
  * [6. Generate unit tests and update tables](#6-generate-unit-tests-and-update-tables)
    * [Add unit tests](#add-unit-tests)
    * [Update tables](#update-tables)
  * [7. Opening a Pull Request](#7-opening-a-pull-request)

# How to add a Publisher

Before contributing a publisher make sure you set up Fundus correctly alongside [these](how_to_contribute.md#setup-fundus) steps.
Then check the [**supported publishers**](supported_publishers.md) table if there is already support for your desired publisher.
In the following, we will walk you through an example implementation of the [*The Intercept*](https://www.theintercept.com/) covering the best practices for adding a new publisher.

**_NOTE:_**: Before proceeding, it's essential to ensure that the publisher you intend to add is crawl-able.
Fundus keeps track of those who aren't in [this issue](https://github.com/flairNLP/fundus/issues/309).
To verify, simply replace the three dots `...` in the code snippet below with the URL of an article from the publisher you wish to add, and run the snippet afterward.
````python
import urllib.request

url = ...

request = urllib.request.Request(url, headers={'User-Agent': 'FundusBot'})

with urllib.request.urlopen(request) as response:
    content = response.read()
````
If you encounter an error like `urllib.error.HTTPError: HTTP Error 403: Forbidden`, it indicates that the publisher uses bot protection, preventing crawling.
In such cases, please comment on the issue mentioned above, mentioning the publisher you attempted to crawl, preferably with its domain name.
This helps keep the list accurate and up-to-date.


## 1. Creating a Parser Stub

Take a look at the file structure in `fundus/publishers`.
Fundus uses the [**ALPHA-2**](https://www.iban.com/country-codes) codes specified in ISO3166 to sort publishers into directories by country of origin.
For example:

- `fundus/publishers/de/` for German publishers
- `fundus/publishers/us/` for US publishers
- ...

In case you don't see a directory labelled with the corresponding country code, feel free to create one. 
Within this directory add a file called `__init__.py` and create a class inheriting the PublisherGroup behaviour.
As an example, if you were to add the US, it should look something like this:

```python
from fundus.publishers.base_objects import PublisherGroup

class US(metaclass=PublisherGroup):
    pass
```

Next, you should open the file `fundus/publishers/__init__.py` and make sure that the class PublisherCollection has an attribute corresponding to your newly added country:

```python
from fundus.publishers.us import US

class PublisherCollection(metaclass=PublisherCollectionMeta):
    us = US
```

Now create an empty file in the corresponding country section using the publishers' name or some abbreviation as the file name.
For The Intercept, the correct country section is `fundus/publishers/us/`, since they are a newspaper based in the United States, with a filename like `the_intercept.py` or `intercept.py`.
We will continue here with `the_intercept.py`.
In the newly created file, add an empty parser class inheriting from `ParserProxy` and a parser version `V1` subclassing `BaseParser`.

``` python
from fundus.parser import ParserProxy, BaseParser


class TheInterceptParser(ParserProxy):
    class V1(BaseParser):
        pass
```

Internally, the `ParserProxy` maps crawl dates to specific versions (`V1`, `V2`, etc.) subclassing `BaseParser`.
Since Fundus' parsers are handcrafted and usually tied to specific layouts, this proxying step helps address changes to the layout.

## 2. Creating a Publisher Specification

Next, add a new publisher specification for the publisher you want to cover.
The publisher specification links information about the publisher, sources from where to get the HTML to parse, and the corresponding parser used by Fundus' `Crawler`.

You can add a new entry to the country-specific `PublisherGroup` in the `__init__.py` of the country section you want to contribute to, i.e. `fundus/publishers/<country_code>/__init__.py`.
For now, we only specify the publisher's name, domain, and parser.
We will cover sources in the next step.

For The Intercept, we add the following entry to `fundus/publishers/us/__init__.py`.

``` python
class US(PublisherGroup):
    TheIntercept = Publisher(
        name="The Intercept",
        domain="https://theintercept.com/",
        parser=TheInterceptParser,
    )
```

If the country section for your publisher did not exist before step 1, please add the `PublisherGroup` to the `PublisherCollection` in `fundus/publishers/__init__.py'`.

### Adding Sources

For your newly added publisher to work you first need to specify where to find articles - in the form of HTML - to parse.
Fundus adopts a unique approach by utilizing access points provided by the publishers, rather than resorting to generic web spiders.
Publishers offer various methods to access their articles, with the most common being RSS feeds, APIs, or sitemaps. 
Presently, Fundus supports RSS feeds and sitemaps by adding them as corresponding `URLSource` using the `source` parameter of `Publisher`.

#### Different `URLSource` types

Fundus provides the following types of `URLSource`, which you can import from `fundus.scraping.html`.

1. `RSSFeed` - specifying RSS feeds
2. `Sitemap` - specifying sitemaps
3. `NewsMap` - specifying a special kind of sitemap displaying only recent articles

Fundus distinguishes between these source types to facilitate crawling only recent articles (`RSSFeed`, `NewsMap`) or an entire website (`Sitemap`).
This differentiation is mainly for efficiency reasons.
Refer to [this](4_how_to_filter_articles#filter-sources) documentation on how to filter for different source types.

**_NOTE:_** When adding a new publisher, it is recommended to specify at least one `Sitemap` and one `RSSFeed` or `NewsMap` (preferred).
If your publisher provides a `NewsFeed`, there is no need to specify an `RSSFeed`.

#### How to specify a `URLSource`

To instantiate an object inheriting from URLSource like `RSSFeed` or `Sitemap`, you first need to find a link to the corresponding feed or sitemap and then set it as the entry point using the `url` parameter of `URLSource`.

##### RSS feeds

Getting links for RSS feeds can vary from publisher to publisher.
Most of the time, you can find them through a quick browser search.
Building an `RSSFeed` looks like this:

````python
from fundus import RSSFeed

RSSFeed("https://theintercept.com/feed/?lang=en")
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
For example, to access The Intercepts' `robots.txt`, use https://theintercept.com/robots.txt in your preferred browser.
This will give you one sitemap link:

```console
Sitemap: https://theintercept.com/sitemap_index.xml
````

Most `Sitemaps`, and sometimes `NewsMaps` as well, will be index maps.
In most cases, the URL will give you an idea of whether or not you are dealing with an index map.
If the sitemap is shown to you in raw XML, as it is with this one from Reuters `https://www.reuters.com/arc/outboundfeeds/news-sitemap-index/?outputType=xml`, you will get something like this:
```
<sitemapindex ... >
   <sitemap>
      <loc>https://www.reuters.com/arc/outboundfeeds/news-sitemap/?outputType=xml</loc>
      <lastmod>2024-06-06T09:45:15.030Z</lastmod>
   </sitemap>
   ...
</sitemapindex>
```

The `<sitemap>`, and especially the `<sitemapindex>` tag, indicates that this is, in fact, an index map pointing to other sitemaps rather than articles.
To address this, `Sitemap` and `NewsMap` will step through the given sitemap recursively by default.
You can alter this behavior or reverse the order in which sitemaps are processed with the `recursive` respectively `reverse` parameters.

Now returning to The Intercept, if you visit the Sitemap Index above you will find one more special Sitemap listed within it:

```console
Sitemap: https://theintercept.com/news-sitemap.xml
````

This link points to a NewsMap, which is a special kind of Sitemap.
To have a look at how to differentiate between those two, refer to [this](#how-to-differentiate-between-sitemap-and-newsmap) section.

**_NOTE:_** If you wonder why you should reverse your sources from time to time, `URLSource`'s should, if possible, yield URLs in descending order by publishing date.

Now building a new `URLSource` for a `NewsMap` covering The Intercept looks like this:

````python
from fundus import NewsMap

NewsMap("https://theintercept.com/news-sitemap.xml")
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
3. If you want to block URLs for the entire publisher use the `url_filter` parameter of `Publisher`.
4. In some cases it can be necessary to append query parameters to the end of the URL, e.g. to load the article as one page. This can be achieved by adding the `query_parameter` attribute of `PublisherSpec` and assigning it a dictionary object containing the key - value pairs: e.g. `{"page": "all"}`. These key  - value pairs will be appended to all crawled URLs.

Now, let's put it all together to specify The Intercept as a new publisher in Fundus:

``` python
class US(PublisherGroup):
    TheIntercept = Publisher(
        name="The Intercept",
        domain="https://theintercept.com/",
        parser=TheInterceptParser,
        sources=[
            RSSFeed("https://theintercept.com/feed/?lang=en"),
            Sitemap(
                "https://theintercept.com/sitemap_index.xml",
                reverse=True,
                sitemap_filter=inverse(regex_filter("post-sitemap")),
            ),
            NewsMap("https://theintercept.com/news-sitemap.xml"),
        ],
    )
```

## 4. Validating the Current Implementation Progress

Now validate your implementation progress by crawling some example articles from your publisher.
The following script fits The Intercept and is adaptable by changing the publisher variable accordingly.

``` python
from fundus import PublisherCollection, Crawler

# Change to:
# PublisherCollection.<country_section>.<publisher_specification>
publisher = PublisherCollection.us.TheIntercept

crawler = Crawler(publisher)

for article in crawler.crawl(max_articles=2, only_complete=False):
    print(article)
```

If everything has been implemented correctly, the script should output text articles like the following.

``` console
Fundus-Article:
- Title: "--missing title--"
- Text:  "--missing plaintext--"
- URL:    https://theintercept.com/2024/06/06/judge-ryan-nelson-israel-trip-gaza-recuse/
- From:   The Intercept
Fundus-Article:
- Title: "--missing title--"
- Text:  "--missing plaintext--"
- URL:    https://theintercept.com/2024/06/06/government-federal-employees-biden-gaza-war/
- From:   The Intercept
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
class TheInterceptParser(ParserProxy):
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

For instance, to extract the title for an article in The Intercept, we can access the `headline` within the `NewsArticle` element through the attribute `ld` of `Precomputed`.

``` python
@attribute
    def title(self) -> Optional[str]:
        return self.precomputed.ld.get_value_by_key_path(["NewsArticle", "headline"])
```

**_NOTE:_** In case a `class` is present in the HTML `meta` tag, it will be appended as a namespace to avoid collisions.
I.e. the content of the following meta tag `<meta class="swiftype" name="author" ...` can be accessed with the key `swiftype:author`.

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

### Extract the ArticleBody

In the context of Fundus, an article's body typically includes multiple paragraphs, and optionally, a summary and several subheadings.
It's important to note that article layouts can vary significantly between publishers, with the most common layouts being:
1. **Wall of text**: Commonly used by US-based publishers, this layout consists of a list of paragraphs without a summary or subheadings.
2. **The Complete**: This layout includes a brief summary following the title and multiple paragraphs grouped into sections separated by subheadings (`ArticleSections`).

![The complete: ArticleBody attribute structure of an example article](images/newspaper_labels_bold.pdf)

To accurately extract the body of an article, use the `extract_article_body_with_selector` function from the parser utilities.
This function accepts selectors for the different body parts as input and returns a parsed `ArticleBody`.
For practical examples, refer to existing parser implementations to understand how everything integrates.


### Checking the free_access attribute

In case your new publisher does not have a subscription model, you can go ahead and skip this step.
If it does, please verify that there is a tag `isAccessibleForFree` within the HTMLs `ld+json` elements (refer to the section [Extracting attributes from Precomputed](#extracting-attributes-from-precomputed) for details) in the source code of premium articles that is set to either `false` or `False`,  `true`/`True` respectively.
It doesn't matter if the tag is missing in the freely accessible articles.
If this is the case, you can continue with the next step. If not, please overwrite the existing function by adding the following snippet to your parser:

```python
@attribute
def free_access(self) -> bool:
    # Your personalized logic goes here
    ...
```

Usually you can identify a premium article by an indicator within the URL or by using XPath or CSSSelector and selecting
the element asking to purchase a subscription to view the article.

### Finishing the Parser

Bringing all the above together, the The Intercept Parser now looks like this.

```python
from datetime import date, datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class TheInterceptParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath(
            "//p[@class='post__excerpt'] | //h2[preceding-sibling::h1[contains(@class, 'post__title')]]"
        )
        _paragraph_selector = CSSSelector("div.entry-content > div.entry-content__content > p, blockquote > p")
        _subheadline_selector = CSSSelector("div.entry-content > div.entry-content__content > h2")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.get_value_by_key_path(["NewsArticle", "author"]))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.ld.get_value_by_key_path(["NewsArticle", "datePublished"]))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.get_value_by_key_path(["NewsArticle", "headline"])

        @attribute
        def topics(self) -> List[str]:
            # The Intercept specifies the article's topics, including other metadata,
            # inside the "keywords" linked data indicated by a "Subject: " prefix.
            # Example keywords: ["Day: Saturday", ..., "Subject: World", ...]
            keywords: Optional[List[str]] = self.precomputed.ld.get_value_by_key_path(["NewsArticle", "keywords"])
            if keywords is None:
                return []

            return [keyword[9:] for keyword in keywords if keyword.startswith("Subject: ")]


```

Now, execute the example script from step 4 to validate your implementation.
If the attributes are implemented correctly, they appear in the printout accordingly.

```console
Fundus-Article:
- Title: "Judge Who Went on Israel Junket Recuses Himself From Gaza Case"
- Text:  "The federal judge hearing a human rights case disputed allegations he might be
          impartial but recused himself out of an “abundance of caution.” [...]"
- URL:    https://theintercept.com/2024/06/06/judge-ryan-nelson-israel-trip-gaza-recuse/
- From:   The Intercept (2024-06-06 19:14)
Fundus-Article:
- Title: "“Not the Career in Public Service I Signed Up For”: Federal Workers Protest War"
- Text:  "Government employees are using their official badges to demonstrate against U.S.
          support for Israel’s war on Gaza.  “My employer is murdering [...]"
- URL:    https://theintercept.com/2024/06/06/government-federal-employees-biden-gaza-war/
- From:   The Intercept (2024-06-06 17:16)
```

## 6. Generate unit tests and update tables

### Add unit tests

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

with <your_publisher_class> being the class name of the `Publisher` your working on.

In our case, we would run:

````shell
python -m scripts.generate_parser_test_files -p TheIntercept
````

to generate a unit test for our parser.

Note: If you need to modify your parser slightly after already adding a unit test, there's no need to create a new test case and load a new HTML file. 
You can simply run the script with the `-oj` flag.

In our scenario, the command would be:

````shell
python -m scripts.generate_parser_test_files -p TheIntercept -oj
````

This command will overwrite the existing `.json` file for your test case while retaining the HTML file.

### Update tables

To fully integrate your new publisher you have to add it to the [supported publishers](supported_publishers.md) table.
You do so by simply running

````shell
python -m scripts.generate_tables
````

Now to test your newly added publisher you should run pytest with the following command:

````shell
pytest
````

## 7. Opening a Pull Request

1. Make sure you tested your parser using `pytest`.
2. Run `black src`, `isort src`, and `mypy src` with no errors.
3. Push and open a new PR
4. Congratulation and thank you very much.
