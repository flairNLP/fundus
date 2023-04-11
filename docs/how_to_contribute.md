# We want you!

First of all: Thank you for thinking about making Fundus better.
We try to tackle news scraping with domain-specific parsers to focus on precise extraction. 
To handle this massive workload, we depend on people like you to contribute.

# What is Fundus

Fundus aims to be a very lightweight but precise news-scraping library.
Easy to use while being able to precisely extract information from provided HTML. 
At its core Fundus is a massive parser library. 
Rather than automate the extraction layer, we build a handcrafted, precise parser.
In consequence,  for Fundus to be able to parse a specific news domain, someone has to write a parser specific to this domain. 
And there are a lot of domains.

# How to contribute

Before contributing a parser, check the [**readme**](../README.md) if there is already support for your desired publisher.
In the following, we will walk you through an example implementation of the [*Los Angeles Times*](https://www.latimes.com/) covering the best practices for adding a news source.

### 1. Library Structure
Take a look at the library architecture in `src/library`. 
Fundus is divided into country-specific sections representing the country a news source originates from.
For example
- `src/library/de/` for German publishers and
- `src/library/us/` for American publishers.

For the Los Angeles Times, the correct location is `src/library/us/los_angeles_times.py` since they are an American publisher.
If your publisher requires a new country section, please add it.

### 2. Parser Stub
In the Python file from step 1, add an empty parser class inheriting from `BaseParser`.
``` python
from src.parser.html_parser import BaseParser

class LosAngelesTimesParser(BaseParser):
    pass
```

### 3. Publisher Specification
Add a new publisher specification for the publisher you want to cover.
The publisher specification includes the publisher's domain, sitemap and the corresponding parser.
You can add a new entry to the country-specific `PublisherEnum` in the `__init__.py` of the country section you want to contribute to, i.e. `src/library/<country_code>/__init__.py`.
For now, we specify the publisher's domain and parser. 
We cover the publisher's sitemap in the next step.

For the Long Angeles Times, we add the following entry to `src/library/us/__init__.py`.
``` python
class US(PublisherEnum):
    LATimes = PublisherSpec(
        domain="https://www.latimes.com/",
        parser=LosAngelesTimesParser,
    )
```

If the country section for your publisher did not exist before step 1, please add the `PublisherEnum` to `src/library/collection/__init__.py'`.

### 4. Publisher Specification Sitemap
The added publisher specification has to specify where to look for articles.
Right now, Fundus has support for reading sitemaps or RSS feeds.
Usually, the publisher's sitemaps are located at the end of `<publisher_domain>/robots.txt` or through a quick Google search.

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
```xml
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
```xml
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" 
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
        xmlns:image="http://www.google.com/schemas/sitemap-image/1.1" 
        xmlns:video="http://www.google.com/schemas/sitemap-video/1.1" 
        xmlns:news="http://www.google.com/schemas/sitemap-news/0.9" 
        xsi:schemaLocation="http://www.sitemaps.org/schemas/sitemap/0.9 http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd">
    <url>
        <loc>https://www.latimes.com/sports/dodgers/story/2023-03-30/dodgers-2023-season-opener-diamondbacks-tv-times-odds</loc>
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

To complete the publisher specification, specify at least
- `sitemaps` spanning the entire website, 
- `news_map` referring to a Google News Sitemap or Google News Index Map or
- `rss_feeds` covering recently published articles.

Given the above information, the publisher specification for the Los Angeles Times should now look like this.
``` python
class US(PublisherEnum):
    LATimes = PublisherSpec(
        domain="https://www.latimes.com/",
        sitemaps=["https://www.latimes.com/sitemap.xml"],
        news_map="https://www.latimes.com/news-sitemap.xml",
        parser=LATimesParser,
    )
```

### 6.
Now validate your progress by replacing everything inside <> of the following script with your information and running it.
``` python
from src import PublisherCollection, Crawler

publisher = PublisherCollection.<your_country_section>.<your_publisher_entry>

crawler = Crawler(publisher)

for article in crawler.crawl(max_articles=2):
    print(article)
```

If everything went well you should see something like this
``` console
Fundus-Article:
- Title: "--missing title--"
- Text:  "--missing plaintext--"
- URL:    https://www.latimes.com/entertainment-arts/tv/story/2023-03-19/sarah-snook-shiv-succession
- From:   LATimes (2023-03-20 19:25)
Fundus-Article:
- Title: "--missing title--"
- Text:  "--missing plaintext--"
- URL:    https://www.latimes.com/california/story/2023-03-18/la-me-bruces-beach-manhattan-beach-new-monument-ceremony
- From:   LATimes (2023-03-20 19:25)
```

Since we didn't add anything to the parser yet, most of the entries are empty. 

Because the parser you just wrote inherits from `BaseParser` it automatically parses the articles `ld+json` and`meta` content located in the article `head`. 
You can access those properties with `article.ld` and `article.meta`.

### 7.
Bring your parser to life and fill it with attributes to parse.
You can do so by decorating the class methods of your parser with the `@attribute` decorator.
In the end, this decorator indicates to the `BaseParser` which class method to use for parsing an attribute. 
Attributes are expected to have a return value and are precisely specified in the [attribute guidelines](attribute_guidelines.md). 
They define the information your parser will extract.

For example, if we want our parser to extract article titles, we would look at the [attribute guidelines](attribute_guidelines.md) and see if there is something defined which matches our expectations.
In the guidelines, we find an attribute called `title` which exactly describes what we want to extract and also an expected return type. 
You must stick to the return types since those will be checked by `pytest`. You're free to do whatever you want locally, but you won't be able to contribute to the repository when your PR isn't compliant with the guidelines.

Now that we have our attribute name, we can start to add it to the parser by defining a class method called `title` and declare it as an attribute with the `@attribute` decorator.
``` python
class LATimesParser(BaseParser):

    @attribute
    def title(self) -> Optional[str]:
        return 'This is a title'
```
Your parser now supports an attribute called `title` which can be directly accessed through `article.title` or `article.extracted['title']`. 
Not all attributes are directly accessible like `title` but all of them can be accessed via the `extracted` attribute of `Article`.

To let your parser extract useful information rather than placeholders, you can have a look at the `ld` and `meta` attributes of `Article`.
Those will be extracted automatically, when present, and are also accessible during parsing therefore within your parsers `Attributes`.
Often useful information about an article like `title`, `author` or `topics` can be found in these two objects.

You can access them inside your parser class via the `precomputed` attribute of `BaseParser`, which holds a dataclass of type `Precomputed`.
This object contains meta-information about the article you're currently parsing.

``` python
@dataclass
class Precomputed:
    html: str
    doc: lxml.html.HtmlElement
    meta: Dict[str, Any]
    ld: LinkedData
    cache: Dict[str, Any]
```

In the following table you can find a short description about the fields of `Precomputed`

<table>
    <tr>
        <th>attr</th>
        <th>description</th>
    </tr>
    <tr>
        <td>html</td>
        <td>The original fetched HTML.</td>
    </tr>
    <tr>
        <td>doc</td>
        <td>The root node of an <code>lxml.html.Etree</code>.</td>
    </tr>
    <tr>
        <td>meta</td>
        <td>The sites meta information extracted from <code>&lt;meta&gt;</code> tags.</td>
    </tr>
    <tr>
        <td>ld</td>
        <td>The linked data extracted from the sites
            <a href="https://json-ld.org/"><code>ld+json</code></a>. 
        </td>
    </tr>
    <tr>
        <td>cache</td>
        <td>A cache specific to the currently parsed site which 
            can be used to share objects between attributes.
            Share objects with the <code>BaseParser.share(...)</code> 
            class-method.
        </td>
    </tr>

</table>

There are many utility functions defined at `src/parser/html_parser/utility.py` to aid you with your attributes.
Make sure to check out other parsers on how to implement specific attributes.

Bringing all above together our parser now looks like this:
``` python
class LATimesParser(BaseParser):

    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(self.precomputed.doc,
                                                  paragraph_selector='.story-stack-story-body > p')
    @attribute
    def date_published(self) -> datetime:
        return generic_date_parsing(self.precomputed.ld.bf_search('datePublished'))

    @attribute
    def authors(self) -> List[str]:
        return generic_author_parsing(self.precomputed.ld.bf_search('author'))

    @attribute
    def title(self) -> Optional[str]:
        return self.precomputed.meta.get('og:title')
```

### 8.
Add a test case for your news source to `tests/resources/` by compressing an example HTML of your publisher to `<publisher_enum>.html.gz`.
In our case that would be `LATimes.html.gz`.
Next specify asserted values your parser should extract from the example HTML in `<news_source_enum_name>.json`.
Currently, we only test the `title, authors, topics` attribute. 
So it should look something like this:
``` json
{
  "title": "High school lacrosse is starting to have an L.A. moment. Here's why"
  "authots": ...
  ...
}
```
Don't worry if your parser does not support all the attributes specified above. 
Only those supported by your parser will be tested.

### 9.
Make sure you tested your parser before opening a PR and once again go through the attributes guidelines and ensure your parser is compliant with them.
