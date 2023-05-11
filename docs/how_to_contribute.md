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

Before contributing to Fundus you should check if you have fundus installed in `editable` mode and using dev-requirements.
If you haven't done this so far or aren't sure about you should
1. Clone the repository
2. Optional but recommended: Create a virtualenv or conda environment
3. Navigate to the root of the repository
4. Run pip install -e .[dev]

## How to add a Publisher

Before contributing a parser, check the [**readme**](../README.md) if there is already support for your desired publisher.
In the following, we will walk you through an example implementation of the [*Los Angeles Times*](https://www.latimes.com/) covering the best practices for adding a news source.

### 1. Creating a Parser Stub
Take a look at the file structure in `fundus/publishers`. 
Fundus is divided into country-specific sections representing the country a news source originates from.
For example
- `fundus/publishers/de/` for German publishers and
- `fundus/publishers/us/` for American publishers
- ...

For the Los Angeles Times, the correct location is `fundus/publishers/us/los_angeles_times.py` since they are an American publisher.
In the newly created file, add an empty parser class inheriting from `BaseParser`.
``` python
from fundus.parser import BaseParser

class LosAngelesTimesParser(BaseParser):
    pass
```

### 2. Creating a Publisher Specification
Add a new publisher specification for the publisher you want to cover.
The publisher specification links the publisher's domain, sitemap and the corresponding parser to the publisher.

You can add a new entry to the country-specific `PublisherEnum` in the `__init__.py` of the country section you want to contribute to, i.e. `fundus/publishers/<country_code>/__init__.py`.
For now, we specify the publisher's domain and parser. 
We cover the publisher's sitemap in the next step.

For the Long Angeles Times, we add the following entry to `fundus/publishers/us/__init__.py`.
``` python
class US(PublisherEnum):
    LosAngelesTimes = PublisherSpec(
        domain="https://www.latimes.com/",
        parser=LosAngelesTimesParser,
    )
```

If the country section for your publisher did not exist before step 1, please add the `PublisherEnum` to `src/library/collection/__init__.py'`.


### 3. Adding Sitemaps
TODO: Introduce Index Maps (Delete from Google News Maps) -> In separate Sections

The added publisher specification has to specify where to look for articles.
Right now, Fundus has support for reading sitemaps or RSS feeds.
Usually, the publisher's sitemaps are located at the end of `<publisher_domain>/robots.txt` or can be found through a quick Google search.

For the Los Angeles Times, jumping to the end of their [robots.txt](https://www.latimes.com/robots.txt) gives us the following information.
``` console
Sitemap: https://www.latimes.com/sitemap.xml
Sitemap: https://www.latimes.com/news-sitemap.xml
```

They specify two sitemaps. 
One [Google News](https://support.google.com/news/publisher-center/answer/9607107?hl=en&ref_topic=9606468) sitemap.
```
https://www.latimes.com/news-sitemap.xml
``` 

And a sitemap for the entire Los Angeles Times website.
```
https://www.latimes.com/sitemap.xml
```

The idea of the Google News sitemap is to give an overview of recent articles while a sitemap spans the entire website.

**_NOTE:_** There is a known issue with Firefox not displaying XML properly. 
You can find a plugin to resolve this issue [here](https://addons.mozilla.org/de/firefox/addon/pretty-xml/)

#### Finding a Google News Sitemap

Accessing [https://www.latimes.com/news-sitemap.xml](https://www.latimes.com/news-sitemap.xml) should yield an XML file like the following.
``` xml
<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
              xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
              xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemapindex.xsd">
    <sitemap>
        <loc>https://www.latimes.com/news-sitemap-content.xml</loc>
        <lastmod>2023-03-30T04:35-04:00</lastmod>
    </sitemap>
    <sitemap>
        <loc>https://www.latimes.com/news-sitemap-latest.xml</loc>
    </sitemap>
</sitemapindex>
```

We see that the actual sitemap refers to other sitemaps. 
Therefore, it is an index map.
Accessing one of these sitemaps, e.g. [https://www.latimes.com/news-sitemap-latest.xml](https://www.latimes.com/news-sitemap-latest.xml), should yield and XML file like the following.
``` xml
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1"
        xmlns:video="http://www.google.com/schemas/sitemap-video/1.1"
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"
        xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
    <url>
        <loc>
            https://www.latimes.com/sports/dodgers/story/2023-03-30/dodgers-2023-season-opener-diamondbacks-tv-times-odds
        </loc>
        <lastmod>2023-03-30</lastmod>
        <news:news>
            <news:publication>
                <news:name>Los Angeles Times</news:name>
                <news:language>eng</news:language>
            </news:publication>
            <news:publication_date>2023-03-30T06:00:25-04:00</news:publication_date>
            <news:title>Dodgers 2023 season opener vs. Diamondbacks: TV times, odds</news:title>
        </news:news>
    </url>
</urlset>
```
The line we are looking for is `xmlns:news="http://www.google.com/schemas/sitemap-news/0.9"`.
Here, the prefix `news` is bound to the namespace `http://www.google.com/schemas/sitemap-news/0.9`. 
This indicates the sitemap is a Google News Sitemap. 
Thus `https://www.latimes.com/news-sitemap.xml` is a Google News Index Map.

#### Finishing the Publisher Specification

To complete the publisher specification, specify at least one of the following parameters:
- `sitemaps` spanning the entire website, 
- `news_map` referring to a Google News Sitemap or Google News Index Map or
- `rss_feeds` covering recently published articles.

Given the above information, the publisher specification for the Los Angeles Times should now look like this.
``` python
class US(PublisherEnum):
    LosAngelesTimes = PublisherSpec(
        domain="https://www.latimes.com/",
        sitemaps=["https://www.latimes.com/sitemap.xml"],
        news_map="https://www.latimes.com/news-sitemap.xml",
        parser=LosAngelesTimesParser,
    )
```


### 4. Validating the Current Implementation Progress
Now validate your implementation progress by crawling some example articles from your publisher. 
The following script fits the Los Angeles Times and is adaptable by changing the publisher variable accordingly.

``` python
from src import PublisherCollection, Crawler

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
- URL:    https://www.latimes.com/entertainment-arts/tv/story/2023-03-19/sarah-snook-shiv-succession
- From:   LosAngelesTimes (2023-03-20 19:25)
Fundus-Article:
- Title: "--missing title--"
- Text:  "--missing plaintext--"
- URL:    https://www.latimes.com/california/story/2023-03-18/la-me-bruces-beach-manhattan-beach-new-monument-ceremony
- From:   LosAngelesTimes (2023-03-20 19:25)
```

Since we didn't add any specific implementation to the parser yet, most entries are empty.


### 5. Implementing the Parser
Bring your parser to life and fill it with attributes to parse.
You can add attributes by decorating the methods of your parser with the `@attribute` decorator.
Attributes are expected to have a return value precisely specified in the [attribute guidelines](attribute_guidelines.md).

For example, if we want our parser to extract article titles, we take the [attribute guidelines](attribute_guidelines.md) and look for a defined attribute which matches our expectations.
In the guidelines, we find an attribute called `title`, which exactly describes what we want to extract and the expected return type. 
You must stick to the specified return types since they are enforced in our unit tests. 
You're free to experiment locally, but you won't be able to contribute to the repository when your PR isn't compliant with the guidelines.

If you have problems implementing your desired publisher feel free to ask questions in the issue [issue](https://github.com/flairNLP/fundus/issues) tab.

Now that we have our attribute name, we add it to the parser by defining a method called `title` and declaring it as an attribute with the `@attribute` decorator.
``` python
class LosAngelesTimesParser(BaseParser):
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
Attributes defined in the [attribute guidelines](attribute_guidelines.md) are additionally defined as `dataclasses.fields`

#### Extracting Attributes from Precomputed
TODO: Unterscheide von extraction aus semi-structured data (ld meta) und xpath/cssselect 

To let your parser extract useful information rather than placeholders, one way is to use the `ld` and `meta` attributes of the `Article`.
These attributes are automatically extracted when present in the HTML and are accessible during parsing time within your parser's attributes.
Often useful information about an article like the `title`, `author` or `topics` can be found in these two objects.
You can access them inside your parser class via the `precomputed` attribute of `BaseParser`, which holds a dataclass of type `Precomputed`.
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

In the following table, you can find a short description of the fields of the `precomputed` attribute.

| Precomputed Attribute | Description                                                                                                                                            |
|-----------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------|
| html                  | The original fetched HTML.                                                                                                                             |
| doc                   | The root node of an `lxml.html.Etree`.                                                                                                                 |
| meta                  | The article's meta-information extracted from `<meta>` tags.                                                                                           |
| ld                    | The linked data extracted from the article's [`ld+json`](https://json-ld.org/)                                                                         |
| cache                 | A cache specific to the currently parsed site which can be used to share objects between attributes. Share objects with the `BaseParser.share` method. |

For example, to extract the title for an article in the Los Angeles Times, we can access the `og:title` through the `meta` precomputed attribute.
``` python
@attribute
def title(self) -> Optional[str]:
    # Use the `get` function to retrieve data from from the `meta` precomputed attribute
    return self.precomputed.meta.get("og:title")
```

There are many utility functions defined at `fundus/parser/utility.py` to aid when implementing parser attributes.
Make sure to check out other parsers on how to implement specific attributes.

#### Extracting Attributes with XPath and CSS-Select

TODO

#### Finishing the Parser

TODO: Test the parser and use precomputed Xpath

Bringing all above together the Los Angeles Times now looks like this.
``` python
from datetime import datetime
from typing import Optional, List

from src.parser.html_parser import attribute, BaseParser, ArticleBody
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_date_parsing,
    generic_author_parsing,
)


class LosAngelesTimesParser(BaseParser):
    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            paragraph_selector=".story-stack-story-body > p",
        )

    @attribute
    def date_published(self) -> datetime:
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

``` console
Fundus-Article:
- Title: "Sarah Snook wasn't sold on 'Succession' at first. Now, she feels a 'sense of loss'"
- Text:  "--missing plaintext--"  # TODO ADD THIS
- URL:    https://www.latimes.com/entertainment-arts/tv/story/2023-03-19/sarah-snook-shiv-succession
- From:   LosAngelesTimes (2023-03-20 19:25)
Fundus-Article:
- Title: "Manhattan Beach mayor apologizes to Bruce's Beach families, unveils new city monument"
- Text:  "--missing plaintext--"  # TODO ADD THIS
- URL:    https://www.latimes.com/california/story/2023-03-18/la-me-bruces-beach-manhattan-beach-new-monument-ceremony
- From:   LosAngelesTimes (2023-03-20 19:25)
```

### 6. Writing Tests
Add a test case to `tests/resources/parser/test_data/<country_section>/` by compressing the HTML of an example article of your publisher to `<publisher_name>.html.gz`, e.g. `LosAngelesTimes.html.gz`.
Next, specify asserted values your parser should extract from the example HTML in `<publisher_name>.json`, e.g. `LosAngelesTimes.json`.
Currently, we only support tests for the `title`, `authors` and `topics` attributes. 

A `LosAngelesTimes.json` may look like the following.
```json
{
  "authors": [
    "Luca Evans"
  ],
  "title": "Victims of Nashville school shooting honored in somber vigil"
}
```

Don't worry if your parser does not support all the attributes specified above. 
Only those supported by your parser will be tested.

Now to test your newly added publisher you should run pytest with the following command:
``` console
pytest
```


### 7. Opening a Pull Request
Make sure you tested your parser before opening a pull request. 
Once again, go through the attributes guidelines and ensure your parser is compliant with them.
