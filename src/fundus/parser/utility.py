import itertools
import json
import re
from collections import defaultdict
from copy import copy
from dataclasses import dataclass, field
from datetime import datetime
from functools import total_ordering
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    Iterable,
    Iterator,
    List,
    Match,
    NamedTuple,
    Optional,
    Pattern,
    Sequence,
    Type,
    Union,
)
from urllib.parse import urljoin

import lxml.html
import more_itertools
import validators
from dateutil import parser
from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.logging import create_logger
from fundus.parser.data import (
    DOM,
    ArticleBody,
    ArticleSection,
    Image,
    LinkedDataMapping,
    TextSequence,
)

logger = create_logger(__name__)


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


@total_ordering
@dataclass(eq=False)
class Node:
    position: int
    node: lxml.html.HtmlElement = field(compare=False)
    _break_selector: ClassVar[XPath] = XPath("*//br")

    # one could replace this recursion with XPath using an expression like this:
    # //*[not(self::script) and text()]/text(), but for whatever reason, that's actually 50-150% slower
    # than simply using the implemented mixture below
    def text_content(self, excluded_tags: Optional[List[str]] = None) -> str:
        guarded_excluded_tags: List[str] = excluded_tags or []

        def _text_content(element: lxml.html.HtmlElement) -> str:
            if element.tag in guarded_excluded_tags:
                return ""
            text = element.text or "" if not isinstance(element, lxml.html.HtmlComment) else ""
            children = "".join([_text_content(child) for child in element.iterchildren()])
            tail = element.tail or ""
            return text + children + tail

        return _text_content(self._get_break_preserved_node())

    def _get_break_preserved_node(self) -> lxml.html.HtmlElement:
        copied_node = copy(self.node)
        for br in self._break_selector(copied_node):
            br.tail = "\n" + br.tail if br.tail else "\n"
        return copied_node

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Node):
            return NotImplemented
        return self.position == other.position

    def __lt__(self, other: "Node") -> bool:
        return self.position < other.position

    def __hash__(self) -> int:
        return hash(self.position)

    def __str__(self) -> str:
        return self.text_content()

    def __repr__(self):
        return f"{type(self).__name__}: {self.text_content()}"

    def __bool__(self):
        return bool(normalize_whitespace(self.text_content()))


class SummaryNode(Node):
    pass


class SubheadNode(Node):
    pass


class ParagraphNode(Node):
    pass


def extract_article_body_with_selector(
    doc: lxml.html.HtmlElement,
    paragraph_selector: XPath,
    summary_selector: Optional[XPath] = None,
    subheadline_selector: Optional[XPath] = None,
) -> ArticleBody:
    # depth first index for each element in tree
    df_idx_by_ref = {element: i for i, element in enumerate(doc.iter())}

    def extract_nodes(selector: XPath, node_type: Type[Node]) -> List[Node]:
        if not selector and node_type:
            raise ValueError("Both a selector and node type are required")

        return [node for element in selector(doc) if (node := node_type(df_idx_by_ref[element], element))]

    summary_nodes = extract_nodes(summary_selector, SummaryNode) if summary_selector else []
    subhead_nodes = extract_nodes(subheadline_selector, SubheadNode) if subheadline_selector else []
    paragraph_nodes = extract_nodes(paragraph_selector, ParagraphNode)
    nodes = sorted(summary_nodes + subhead_nodes + paragraph_nodes)

    if not nodes:
        # return empty body if no text is present
        return ArticleBody(TextSequence([]), [])

    instructions = more_itertools.split_when(nodes, pred=lambda x, y: type(x) != type(y))

    if not summary_nodes:
        instructions = more_itertools.prepend([], instructions)
    elif not nodes[: len(summary_nodes)] == summary_nodes:
        raise ValueError(f"All summary nodes should be at the beginning of the article")

    if not subhead_nodes or (paragraph_nodes and subhead_nodes[0] > paragraph_nodes[0]):
        first = next(instructions)
        instructions = itertools.chain([first, []], instructions)

    summary = TextSequence(
        map(lambda x: normalize_whitespace(x.text_content(excluded_tags=["script"])), next(instructions))
    )
    sections: List[ArticleSection] = []

    for chunk in more_itertools.chunked(instructions, 2):
        if len(chunk) == 1:
            chunk.append([])
        texts = [list(map(lambda x: normalize_whitespace(x.text_content(excluded_tags=["script"])), c)) for c in chunk]
        sections.append(ArticleSection(*map(TextSequence, texts)))

    return ArticleBody(summary=summary, sections=sections)


_ld_node_selector = XPath("//script[@type='application/ld+json']")
_json_pattern = re.compile(r"(?P<json>{[\s\S]*}|\[\s*{[\s\S]*}\s*](?!\s*}))")


def extract_json_from_dom(root: lxml.html.HtmlElement, selector: XPath) -> Iterable[Dict[str, Any]]:
    def sanitize(text: str) -> Optional[str]:
        # capture only content enclosed as follows: {...} or [{...}]
        match = re.search(_json_pattern, text)
        if match is not None and (sanitized := match.group("json")):
            return sanitized
        return None

    json_nodes = selector(root)
    jsons = []
    for node in json_nodes:
        json_content = sanitize(node.text_content()) or ""
        try:
            jsons.append(json.loads(json_content))
        except json.JSONDecodeError as error:
            logger.debug(f"Encountered {error!r} during JSON parsing")
    return more_itertools.collapse(jsons, base_type=dict)


def get_ld_content(root: lxml.html.HtmlElement) -> LinkedDataMapping:
    """Parse JSON-LD from HTML.

    This function parses a script tags of type ld+json.
    In case the JSON is wrapped in a CDATA tag it is first stripped.

    Args:
        root: The HTML document given as a lxml.html.HtmlElement.

    Returns:
        The JSON-LD data as a LinkedDataMapping
    """

    return LinkedDataMapping(extract_json_from_dom(root, _ld_node_selector))


_meta_node_selector = CSSSelector("head > meta, body > meta")


def get_meta_content(root: lxml.html.HtmlElement) -> Dict[str, str]:
    """Parse metadata from HTML.

    This function parses single values (i.e. charset=...), nodes containing name, property, http-equiv or
    itemprop attributes. When multiple values for the same key occur, they will be joined using `,`. This
    is in order to ease typing and avoid list as additional type.

    In case an HTML tag consists a class, it will be appended as namespace to avoid key collisions.
    I.e. <meta class="swiftype" name="author" ... > will be stored using `swiftype:author` as a key.

    Args:
        root: The HTML document given as a lxml.html.HtmlElement.

    Returns:
        The metadata as a dictionary
    """
    data = defaultdict(list)
    for node in _meta_node_selector(root):
        attributes = node.attrib
        if len(attributes) == 1:
            data[attributes.keys()[0]].append(attributes.values()[0])
        elif key := (  # these keys are ordered by frequency
            attributes.get("name")
            or attributes.get("property")
            or attributes.get("http-equiv")
            or attributes.get("itemprop")
        ):
            if ns := attributes.get("class"):
                key = f"{ns}:{key}"
            if content := attributes.get("content"):
                data[key].append(content)

    metadata: Dict[str, str] = {}
    for name, listed_content in data.items():
        if len(listed_content) == 1:
            metadata[name] = listed_content[0]
        else:
            # for ease of typing we join multiple contents for the same key using ','
            metadata[name] = ",".join(listed_content)

    return metadata


def strip_nodes_to_text(text_nodes: List[lxml.html.HtmlElement], join_on: str = "\n\n") -> Optional[str]:
    if not text_nodes:
        return None
    return join_on.join(([re.sub(r"\n+", " ", node.text_content()) for node in text_nodes])).strip()


def generic_nodes_to_text(nodes: Sequence[Union[lxml.html.HtmlElement, str]], normalize: bool = False) -> List[str]:
    if not nodes:
        return []

    texts = []
    for node in nodes:
        if isinstance(node, lxml.html.HtmlElement):
            text = str(node.text_content())
        elif isinstance(node, str):
            text = node
        else:
            raise TypeError(f"Unexpected type {type(node)}")

        if normalize:
            text = normalize_whitespace(text)

        if text:
            texts.append(text)

    return texts


def apply_substitution_pattern_over_list(
    input_list: List[str], pattern: Pattern[str], replacement: Union[str, Callable[[Match[str]], str]] = ""
) -> List[str]:
    return [subbed for text in input_list if (subbed := re.sub(pattern, replacement, text).strip())]


def generic_author_parsing(
    value: Union[
        Optional[str],
        Dict[str, str],
        List[str],
        List[Dict[str, str]],
    ],
    split_on: Optional[List[str]] = None,
    normalize: bool = True,
) -> List[str]:
    """This function tries to parse the given <value> to a list of authors (List[str]) based on the type of value.

    Parses based on type of <value> as following:
        value (None):       Empty list \n
        value (str):        re.split(delimiters) with delimiters := split_on or common delimiters' \n
        value (dict):       If key "name" in dict, [dict["name"]] else empty list \n
        value (list[str]):  value\n
        value (list[dict]): [dict["name"] for dict in list if dict["name"]] \n

    with common delimiters := [",", ";", " und ", " and ", " & ", " | "]

    All values are stripped with default strip() method before returned.

    Args:
        value: An input value representing author(s) which get parsed based on type.
        split_on: Only relevant for type(<value>) = str. If set, split <value> on <split_on>,
            else (default) split <value> on common delimiters.
        normalize: If True, normalize every autor with normalize_whitespace(). Defaults to True

    Returns:
        A parsed and striped list of authors
    """

    common_delimiters = [",", ";", " und ", " and ", " & ", " \| "]

    parameter_type_error: TypeError = TypeError(
        f"<value> '{value}' has an unsupported type {type(value)}. "
        f"Supported types are 'Optional[str], Dict[str, str], List[str], List[Dict[str, str]],'"
    )

    def parse_author_dict(author_dict: Dict[str, str]) -> Optional[str]:
        if (author_name := author_dict.get("name")) is not None:
            return author_name

        given_name = author_dict.get("givenName", "")
        additional_name = author_dict.get("additionalName", "")
        family_name = author_dict.get("familyName", "")
        if given_name and family_name:
            return " ".join(filter(bool, [given_name, additional_name, family_name]))
        else:
            return None

    if not value:
        return []

    # collapse
    authors: List[str] = []

    for item in value if isinstance(value, list) else [value]:
        if isinstance(item, str):
            authors.append(item)

        elif isinstance(item, dict):
            if (author := parse_author_dict(item)) is not None:
                authors.append(author)

        else:
            raise parameter_type_error

    if normalize or split_on:

        def split(text: str) -> Iterable[str]:
            return filter(bool, re.split(r"|".join(split_on or common_delimiters), text))

        authors = list(more_itertools.flatten([split(author) for author in authors]))
        normalized_authors = [normalize_whitespace(author) for author in authors]
        return normalized_authors

    return authors


def generic_text_extraction_with_css(doc, selector: XPath) -> Optional[str]:
    nodes = selector(doc)
    return strip_nodes_to_text(nodes)


def generic_topic_parsing(keywords: Optional[Union[str, List[str]]], delimiter: str = ",") -> List[str]:
    if not keywords:
        return []
    elif isinstance(keywords, str):
        return [cleaned for keyword in keywords.split(delimiter) if (cleaned := keyword.strip())]
    elif isinstance(keywords, list) and all(isinstance(s, str) for s in keywords):
        return keywords
    else:
        raise TypeError(f"Encountered unexpected type {type(keywords)} as keyword parameter")


_tz_infos = {"CET": 3600, "CEST": 7200}


def generic_date_parsing(date_str: Optional[str]) -> Optional[datetime]:
    return parser.parse(date_str, tzinfos=_tz_infos) if date_str else None


_title_selector = CSSSelector("title")


def parse_title_from_root(root: lxml.html.HtmlElement) -> Optional[str]:
    title_node = _title_selector(root)

    if len(title_node) != 1:
        return None

    return strip_nodes_to_text(title_node)


def preprocess_url(url: str, domain: str) -> str:
    url = re.sub(r"\\/", "/", url)
    # Some publishers use relative URLs
    if not validators.url(url):
        publisher_domain = "https://" + domain
        url = urljoin(publisher_domain, url)
    return url


def image_author_parsing(authors: Union[str, List[str]], author_filter: Optional[Pattern[str]] = None) -> List[str]:
    def clean(author: str):
        author = re.sub(r"©|((f|ph)oto|image)\s*(by|:)", "", author, flags=re.IGNORECASE)
        if author_filter:
            author = re.sub(author_filter, "", author)
        return author.strip()

    if isinstance(authors, list):
        authors = [clean(author) for author in authors]
    else:
        authors = clean(authors)
    return generic_author_parsing(authors)


class Bounds(NamedTuple):
    upper: int
    first_paragraph: Optional[int]
    lower: int


class IndexedImageNode(NamedTuple):
    position: int
    content: lxml.html.HtmlElement
    is_cover: bool


# https://regex101.com/r/MplUXL/2
_srcset_pattern = re.compile(r"(?P<url>[^\s]+)\s*(?P<descriptor>[0-9.]+[wx])?(,?\s*)")


def parse_srcset(srcset: str) -> Dict[str, str]:
    # Updated regular expression to account for query parameters in URLs
    urls = {}
    for match in _srcset_pattern.finditer(srcset.strip()):
        url = match.group("url")
        descriptor = match.group("descriptor")  # Width (w) or pixel density (x)
        urls[descriptor or "1x"] = url
    # return sorted dict based on int value of descriptor
    return dict(sorted(urls.items(), key=lambda item: int(item[0][:-1])))


def parse_urls_from_image(node: lxml.html.HtmlElement) -> Optional[Dict[str, str]]:
    if srcset := (node.get("data-srcset") or node.get("srcset")):
        return parse_srcset(srcset)
    elif src := (node.get("data-src") or node.get("src")):
        return {"1x": src}
    else:
        return None


def parse_image_node(
    image_nodes: List[IndexedImageNode],
    caption_selector: XPath,
    alt_selector: XPath,
    author_selector: Union[XPath, Pattern[str]],
    author_filter: Optional[Pattern[str]] = None,
) -> Iterator[Image]:
    """Extract urls, caption, description and authors from a list of <img> nodes

    Args:
        image_nodes: Indexed <img> nodes to parse
        caption_selector: Selector selecting the caption of an image. Defaults to selecting the figcaption element.
        alt_selector: Selector selecting the descriptive text of an image. Defaults to selecting alt value.
        author_selector: Selector selecting the credits for an image. Defaults to selecting an arbitrary child of
            figure with copyright or credit in its class attribute.
        author_filter: In case the author_selector cannot adequately select the author, this filter can be used to
            remove unwanted substrings

    Returns:
        List of Images
    """

    def nodes_to_text(nodes: List[Union[lxml.html.HtmlElement, str]]) -> Optional[str]:
        return " ".join(generic_nodes_to_text(nodes, normalize=True)) or None

    for position, node, is_cover in image_nodes:
        urls = {}
        if (parent := node.getparent()) is not None and parent.tag == "picture":
            for source in parent.xpath("./source"):
                urls.update(parse_urls_from_image(source) or {})
        else:
            urls.update(parse_urls_from_image(node) or {})
        if not urls:
            continue

        # parse caption
        caption = nodes_to_text(caption_selector(node))

        # parse authors
        authors = []
        if isinstance(author_selector, Pattern):
            # author is part of the caption
            if caption and (match := re.search(author_selector, caption)):
                authors = [match.group("credits")]
                caption = re.sub(author_selector, "", caption).strip() or None
        else:
            if author_nodes := author_selector(node):
                authors = generic_nodes_to_text(author_nodes, normalize=True)
        authors = image_author_parsing(authors, author_filter)

        # parse description
        description = nodes_to_text(alt_selector(node))

        yield Image(
            urls=urls,
            caption=caption,
            authors=authors,
            description=description,
            is_cover=is_cover,
            position=position,
        )


def determine_bounds(
    dom: DOM, paragraph_selector: XPath, upper_boundary_selector: XPath, lower_boundary_selector: Optional[XPath]
) -> Optional[Bounds]:
    def get_sorted_indices(nodes: List[lxml.html.HtmlElement]) -> List[int]:
        return sorted([dom.get_index(node) for node in nodes])

    # the getitem on upper_boundary_selector ensures that this throws an exception, if there are no
    # upper_boundary_node present, as well as removing excess ones.
    upper_boundary_nodes = [upper_boundary_selector(dom.root)[0]]
    paragraph_nodes = paragraph_selector(dom.root)
    lower_boundary_nodes = lower_boundary_selector(dom.root) if lower_boundary_selector else []

    sorted_indices = get_sorted_indices(upper_boundary_nodes + paragraph_nodes + lower_boundary_nodes)

    if len(sorted_indices) < 2:
        return None

    return Bounds(
        upper=sorted_indices[0],
        first_paragraph=paragraph_indices[0] if (paragraph_indices := get_sorted_indices(paragraph_nodes)) else None,
        lower=sorted_indices[-1],
    )


def image_extraction(
    doc: lxml.html.HtmlElement,
    paragraph_selector: XPath,
    image_selector: XPath = XPath("//figure//img"),
    upper_boundary_selector: XPath = XPath("//main"),
    lower_boundary_selector: Optional[XPath] = None,
    caption_selector: XPath = XPath("./ancestor::figure//figcaption"),
    alt_selector: XPath = XPath("./@alt"),
    author_selector: Union[XPath, Pattern[str]] = XPath(
        "(./ancestor::figure//*[(contains(@class, 'copyright') or contains(@class, 'credit')) and text()])[1]"
    ),
    author_filter: Optional[Pattern[str]] = None,
) -> List[Image]:
    """Extracts images enriched with metadata from <dom> based on given selectors.

    The core idea behind this function is to select all images matching <image_selector> that lay between
    the first element selected by <upper_boundary_selector> and the last element of <lower_boundary_selector>
    or <paragraph_selector>. The hierarchy is determined by indexing all nodes of <doc> depth first.
    To enrich the selected images with metadata like 'caption', 'alt-description' or `authors`, one should make
    use of the corresponding selectors.

    Args:
        doc: The html document of the article.
        paragraph_selector: Selector used to select the paragraphs of the article.
        image_selector: Selector selecting all relevant img elements. Defaults '//figure//img'.
        upper_boundary_selector: A selector referencing an element to be considered as the upper boundary. All img
            elements before this element will be ignored.
        lower_boundary_selector: A selector referencing an element to be considered as the lower boundary. All img
            elements after this element will be ignored. Defaults to the last paragraph of an article.
        caption_selector: Selector selecting the caption of an image. Defaults to selecting the figcaption element.
        alt_selector: Selector selecting the descriptive text of an image. Defaults to selecting alt value.
        author_selector: Selector selecting the credits for an image. Defaults to selecting an arbitrary child of
            figure with copyright or credit in its class attribute.
        author_filter: In case the author_selector cannot adequately select the author, this filter can be used to
            remove unwanted substrings.

    Returns:
        A list of Images contained within the article

    """

    # index nodes df
    dom = DOM(doc)

    # determine bounds based on df index
    if not (bounds := determine_bounds(dom, paragraph_selector, upper_boundary_selector, lower_boundary_selector)):
        raise ValueError("Bounds could not be determined")

    image_nodes = [
        IndexedImageNode(position=position, content=node, is_cover=position < (bounds.first_paragraph or 0))
        for node in image_selector(doc)
        if bounds.upper < (position := dom.get_index(node)) < bounds.lower
    ]

    images = list(
        parse_image_node(
            image_nodes=image_nodes,
            caption_selector=caption_selector,
            alt_selector=alt_selector,
            author_selector=author_selector,
            author_filter=author_filter,
        )
    )

    return images
