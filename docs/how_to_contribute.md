# We want you!

First of all: Thank you for thinking about making fundus better.
We try to tackle news scraping with domain-specific
parsers to focus on precise extraction. To handle
this massive workload, we depend on people like you to contribute.

# What is fundus

Fundus aims to be a very lightweight but precise news-scraping library.
Easy to use while being able to precisely extract information from
provided HTML. This is possible because fundus, at it's core, is
a massive parser library and rather than automate the extraction
layer, we build on handcrafted, and therefore precise, parser.
This also means: For fundus being able to parse a specific news domain,
someone has to write a parser specific to this domain. And there are
a lot of domains.

# How to contribute

If you want to be a part of this project, here are some steps on how to contribute.

## News Source

Before contributing a parser, check the [**readme**](../README.md) if there is already 
support for your desired publisher.

In the following, we will walk you through an example implementation covering the best practised for adding a news source.

#### 1.
Get used to the library architecture in `src/library`. Fundus is divided into country-specific sections
(`/library/at/, /library/de/, ..., /library/us/`) representing the country a news source originates from. In our
case, the correct location we're operating on is `/library/us/`.

#### 2.
Add an empty parser class which inherits from `BaseParser` at the desired country location in the library. Following
the example of contributing a parser for the LA Times, we would add something like this:
``` python
class LATimesParser(BaseParser):
    pass
```
to a new file at `src/library/us/la_times_parser.py`.

#### 3.
Add a new specification for the publisher/domain you want to cover. You do so by adding a new entry 
(or entire PublisherEnum if it doesn't exist yet) to the country specific `PublisherEnumm` in the `__init__.py` of 
the country section you want to contribute to. The `__init__` can be found at `/library/<country_code>/__init__.py`.

If the country section you are contributing to didn't exist till now you also have to add it to 
`/library/collection/__init__.py'`.

To continue our journey of adding the LA Times to fundus we would add an entry to the class `US(PublisherEnum)` 
located at `/library/us/__init__.py` which would look like the this.

``` python
class US(PublisherEnum):
    LATimes = PublisherSpec(domain='https://www.latimes.com/',
                            parser=LATimesParser)
```

#### 4.
Now try running your news source with the following lines of code.
``` python
from src import PublisherCollection, Crawler

crawler = Crawler(PublisherCollection.us.<your_news_source>)

for article in crawler.crawl(max_articles=2):
    print(article)
```
This will raise the following error 
```
ValueError: Publishers must at least define either an rss-feed, sitemap or news_map to crawl
```
since we didn't specify yet where to look for articles.

#### 5.
To work, your newly added source has to specify a location where to look for articles. Right now fundus has support for
reading sitemaps or rss feeds. You usually find sitemaps for the news source you want to add at the end of 
`<your_news_source_domain>/robots.txt` or through a quick google search.

In our case jumping to the end of `https://www.latimes.com/robots.txt` gives us the following information.
``` console
Sitemap: https://www.latimes.com/sitemap.xml
Sitemap: https://www.latimes.com/news-sitemap.xml
```

Here we see two sitemaps specified. One 
[Google News](https://support.google.com/news/publisher-center/answer/9607107?hl=en&ref_topic=9606468) sitemap 
`https://www.latimes.com/news-sitemap.xml` and a sitemap for the entire LA Times website 
`https://www.latimes.com/sitemap.xml`. The idea of the news sitemap is to give an overview
over recent articles while the other one spans the entire website. To get your news source running you have to
specify either `sitemaps` (spanning the entire website), a `news_map` (referring to a Google News map) or `rss_feeds` 
covering recently published articles.

Given the above information our entry should look like this now:
``` python
    LATimes = PublisherSpec(
        domain="https://www.latimes.com/",
        sitemaps=["https://www.latimes.com/sitemap.xml"],
        news_map="https://www.latimes.com/news-sitemap.xml",
        parser=LATimesParser,
    )
```

#### 6.
Now validate your progress by replacing everything inside <> of the following script with your information and 
running it.
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

Since we didn't add anything to the parser yet most of the entries are empty. 

Because the parser you just wrote inherits from `BaseParser` it automatically parses the articles `ld+json` and 
`meta` content located in the article `head`. You can access those properties with `article.ld` and `article.meta`.

#### 7.
Bring your parser to life and fill it with `Attribute`'s to parse.
You can do so by decorating the class methods of your parser with the `@attribute` decorator.
In the end this decorator indicates to the `BaseParser` which class method to use for parsing an attribute. 
`Attributes`'s are expected to have a return value and are precisely specified in the 
[attribute_guidelines](attribute_guidelines.md). They define the information your parser will extract.

For example, if we want our parser to extract article titles, we would look at the 
[attribute_guidelines](attribute_guidelines.md) and see if there is something defined which matches our expectations.
In the guidelines we find an attribute called `title` which exactly describes what we want to extract and also
an expected return type. It is very important that you stick to the return types since those will be enforced
at run time and otherwise an error will be thrown.

Now that we have our attribute name we can start to add it to the parser by defining a class method called `title`
and declare it as an attribute with the `@attribute` decorator.
``` python
class LATimesParser(BaseParser):

    @attribute
    def title(self) -> Optional[str]:
        return 'This is a title'
```
Your parser now supports an `Attribute` called `title` which can be directly accessed through `article.title` or 
`article.extracted['title']`. Not all `Attributes` are directly accessible like `title` but all of them can be 
accessed via the `extracted` attribute of `Article`.

To let your parser extract useful information rather than placeholders, you can have a look at the `ld` and `meta`
attributes of `Article`. Those will be extracted automatically, when present, and are also accessible during parsing
therefore within your parsers `Attributes`. Often useful information about an article like `title`, `author` or 
`topics` can be found in these two objects.

You can access them inside your parser class via the `precomputed` attribute of `BaseParser`, which holds a dataclass 
of type `Precomputed`. This object contains meta-information about the article you're currently parsing.

``` python
@dataclass
class Precomputed:
    html: str
    doc: lxml.html.HtmlElement
    meta: Dict[str, Any]
    ld: LinkedData
    cache: Dict[str, Any]
```

Here `html` is the original html to parse, `doc` is a root node from a `lxml.html.Etree`,
`meta` is the meta information extracted from the html's meta tags, `ld` is the linked data
parsed from the html's `ld+json` and `cache` a cache specific to the html which can be used to
share objects between class methods. In order to do so use the `share` class method.

There are many utility functions defined at `src/parser/html_parser/utility.py` to aid you with
your attributes. Make sure to check out other parsers on how to write specific attributes.

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

#### 8.
Add a test case for your news source to `tests/resorces/` by compressing an example html of your news_source to 
`<news_source_enum_name>.html.gz` in our case `LATimes.html.gz` and specifying asserted values your parser should 
extract from the example html in `<news_source_enum_name>.json`
Currently, we only test on `title` so it should look something like this.
``` json
{
  "title": "High school lacrosse is starting to have an L.A. moment. Here's why"
}
```

#### 9.
Make sure you tested your parser before opening a PR and once again go through the attributes
guidelines and ensure your parser is compliant with whatever is being specified there.
