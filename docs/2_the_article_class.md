# The Article class

This tutorial introduces the article class and how to access the parsed data.

## Article Overview

The `Article` class is the base data container Fundus uses to store information about an article.
It contains the parsed attributes as well as the article's origin.

Printing titles works like this:

````python
from fundus import Crawler, PublisherCollection

crawler = Crawler(PublisherCollection.us)

for article in crawler.crawl(max_articles=2):
    print(article.title)  # <- you can use any kind of attribute access Python supports on objects here
````

This will print something like:

```console
Shutterstock shares pop as company expands partnership with OpenAI
Donald Trump asks judge to delay classified documents trial
```

The file [**attribute guidelines**](attribute_guidelines.md) contains a list of supported attributes.
All attributes listed here can be accessed through the `Article` class.

**_NOTE:_** The listed attributes represent attributes of the `Article` dataclass with all of them having default
values.

Some parsers may support additional attributes not listed in the guidelines.
You can find those attributes under the [**supported publisher**](supported_publishers.md) tables
under `Additional Attributes`.

**_NOTE:_** Keep in mind that these additional attributes are specific to a parser and cannot be accessed for every
article.

Sometimes an attribute listed in the attribute guidelines isn't supported at all by a specific parser.
You can find this information under the `Missing Attributes` tab within the supported publisher tables.
There is also a built-in search mechanic you can learn about [here](4_how_to_search_for_publishers.md)

## The articles' body

Fundus supports two methods to access the body of the article

1. Accessing the `plaintext` property of `Article` with `article.plaintext`.
   This will return a cleaned and formatted version of the article body as a single string object and should be suitable
   for most use cases. <br>
   **_NOTE:_** The different DOM elements are joined with two new lines and cleaned with `split()` and `' '.join()`.
2. Accessing the `body` attribute of `Article`. This returns an `ArticleBody` instance, granting more fine-grained
   access to the DOM structure of the article body.

Printing the headline and paragraphs for the last section of the article body works like this:

````python
from fundus import Crawler, PublisherCollection
from textwrap import TextWrapper

crawler = Crawler(PublisherCollection.us.CNBC)
wrapper = TextWrapper(width=80, max_lines=1)

for article in crawler.crawl(max_articles=1):
    last_section = article.body.sections[-1]
    if last_section.headline:
        print(wrapper.fill(f"This is a headline: {last_section.headline}"))
    for paragraph in last_section.paragraphs:
        print(wrapper.fill(f"This is a paragraph: {paragraph}"))
````

Will print something like this:

```console
This is a headline: Even a proper will is superseded in some cases
This is a paragraph: A will is superseded in some cases, such as with [...]
This is a paragraph: That may also happen if a decedent owns property in [...]
This is a paragraph: "You have to also look at how your assets are [...]
This is a paragraph: When someone dies, the executor presents their will [...]
This is a paragraph: People who would like to keep the details of their [...]
```

**_NOTE:_** Not all publishers support the layout format shown above.
Sometimes headlines or the entire summary are missing.
You can always check the specific parser what to expect, but even within publishers, the layout differs from article to
article.

## HTML

Fundus keeps track of the origin of each article.
You can access this information with the `html` attribute of `Article`.
This attribute contains the following information:

1. `requested_url: str`: The original URL used to request the HTML.
2. `responded_url: str`: The URL attached to the server response.
   Often the same as `requested_url: str`; can change with redirects.
3. `content: str`: The HTML content.
4. `crawl_date: datetime`: The exact timestamp the article was crawled.
5. `source: HTMLSource`: The internal source object the article originates from.

## Language detection

Sometimes publishers support articles in different languages.
To address this Fundus implements native support for language detection.
You can access the detected language with `Article.lang`.

Printing some languages for our articles works like this:

````python
from fundus import Crawler, PublisherCollection

crawler = Crawler(PublisherCollection.us)

for article in crawler.crawl(max_articles=1):
    print(article.lang)
````

Should print this:
``console
en
``

In the [**next section**](3_how_to_filter_articles.md) we will show you how to filter articles.
