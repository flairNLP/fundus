# We want you!

First of all: Thank you for thinking about making fundus better.
We try to answer news scraping with the implementation of domain specific
parser to focus on precise extraction. In order to be able to handle
this massive workload, we depend on people like you to contribute.

# What is fundus

fundus aims to be a very lightweight but precises news scraping library.
Easy to use while being able to precisely extract information from
provided html. This is possible because fundus, at it's core, is
a massive parser library and rather than automate the extraction
layer, we build on handcrafted, and therefore precise, parser.
This also means: For fundus being able to parse a specific news domain,
someone has to write a parser specific to this domain. And there are
a lot of domains.

# How to contribute

If you want to be a part of this project, here are some steps on how to contribute

## Parser

To contribute a parser you should follow these steps:

#### 1.

Get used to the library (`src/library`) architecture and add a new specification for your desired
publisher/domain. The individual collection are found under `src/library/<language_code>/__init__.py`.
The collection will automatically parse sitemaps found at the specified domain's `robots.txt`, but will
be overwritten when this information is given in the specification. The rss-feeds are not gathered
automatically and can only be set via the specification.

#### 2.

Get used to the `BaseParser` architecture. Every parser you write will ultimately
inherit from `BaseParser`.

#### 3.

Bring your parser to life and fill it with `Attribute`'s or `Function`'s.
You can do so by decorating the class methods of your parser either with `@attribute` or `@function`.
In the end those decorators decide how your methode will be treated in the workflow. `Attributes`'s are expected to
have a return value and are precisely specified in the `attribute_guidelines`. They define the information
your parser will extract. `Function`'s control the flow of your parser and are expected to have no return.
They can be used to define additional steps like rendering the html etc. Both `Attribute`'s and `Function`'s
will be called in lexicographical order, but can be given a priority via the decorators, with 0 having
the highest and `None` the lowest. Your class methods have access to precomputed information
via the `preecomputed` attribute of `BaseParser`.

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

#### 4.

Make sure you tested your parser before opening a PR and once again go through the attributes
guidelines and ensure your parser is compliant with whatever is being specified there.
