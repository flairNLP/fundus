from __future__ import annotations

import html
import itertools
import json
import re
from collections import defaultdict
from copy import copy
from dataclasses import dataclass, field
from datetime import datetime
from functools import total_ordering
from typing import (
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
    Set,
    Type,
    Union,
    cast,
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
    Dimension,
    Image,
    ImageVersion,
    LinkedDataMapping,
    TextSequence,
)
from fundus.utils.regex import _get_match_dict
from fundus.utils.serialization import JSONVal

logger = create_logger(__name__)

_space_characters = {
    "whitespace": r"\s",
    "non-breaking-space": r"\u00A0",
    "zero-width-space": r"\u200B",
    "zero-width-non-joiner": r"\u200C",
    "zero-width-joiner": r"\u200D",
    "zero-width-no-break_space": r"\uFEFF",
}
_ws_pattern: Pattern[str] = re.compile(rf'[{"".join(_space_characters.values())}]+')


def normalize_whitespace(text: str) -> str:
    return re.sub(_ws_pattern, " ", text).strip()


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
                return element.tail or ""
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
_json_undefined = re.compile(r'(?P<key>"[^"]*?"):\s*undefined')


def sanitize_json(text: str) -> Optional[str]:
    # capture only content enclosed as follows: {...} or [{...}]
    match = re.search(_json_pattern, text)
    if match is None or not (sanitized := match.group("json")):
        return None

    # substitute "bad" values
    sanitized = re.sub(_json_undefined, r"\g<key>:null", sanitized)
    sanitized = re.sub(r"[\r\n\t]+", "", sanitized)
    return sanitized


def unescape_json_values(obj):
    if isinstance(obj, str):
        return html.unescape(obj)
    elif isinstance(obj, list):
        return [unescape_json_values(item) for item in obj]
    elif isinstance(obj, dict):
        return {key: unescape_json_values(value) for key, value in obj.items()}
    else:
        return obj


def parse_json(text: str) -> Optional[Dict[str, JSONVal]]:
    if not (json_content := sanitize_json(text)):
        return None

    try:
        parsed_json = json.loads(json_content)
        return cast(Dict[str, JSONVal], unescape_json_values(parsed_json))
    except json.JSONDecodeError as error:
        logger.debug(f"Encountered {error!r} during JSON parsing")
        return None


def extract_json_from_dom(root: lxml.html.HtmlElement, selector: XPath) -> Iterable[Dict[str, JSONVal]]:
    jsons = [parsed_json for node in selector(root) if (parsed_json := parse_json(node.text_content())) is not None]
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


_meta_node_selector = CSSSelector("head > meta, body > meta, article > meta")


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


def transform_breaks_to_paragraphs(element: lxml.html.HtmlElement, **attribs: str) -> lxml.html.HtmlElement:
    """Splits the content of <element> on <br> tags into paragraphs and transform them in <p> elements.

    Args:
        element: The element on which to perform the transformation
        **attribs: The attributes of the wrapped paragraphs as keyword arguments. I.e. the
            default {"class": "br-wrap"} wil produce the following elements: <p class='br-wrap'>.
            To use python keywords wrap them dunder scores. __class__ for class.

    Returns:
        The transformed element
    """

    if not attribs:
        attribs = {"class": "br-wrap"}
    else:
        attribs = {re.sub(r"^__(.*?)__$", r"\1", key): value for key, value in attribs.items()}

    def get_paragraphs() -> List[str]:
        raw_html = lxml.etree.tostring(element, method="html", encoding="unicode")
        if match := re.match(r"^<[^>]*?>\s*(?P<content>.*?)\s*<[^>]*?>\s*$", raw_html, re.S):
            content = match.group("content")
            return list(filter(bool, (text.strip() for text in content.split("<br>"))))
        return []

    def generate_attrs() -> str:
        return " ".join([f"{attribute}='{value}'" for attribute, value in attribs.items()]) if attribs else ""

    def clear_element():
        for child in element:
            element.remove(child)
        element.tail = None
        element.text = None

    # split content on <br> tags
    if not (paragraphs := get_paragraphs()):
        return element

    # remove children, tail and text from element
    clear_element()

    # add paragraphs to cleared element
    for paragraph in paragraphs:
        wrapped = f"<p{' ' + generate_attrs()}>{paragraph}</p>"
        element.append(lxml.html.fromstring(wrapped))

    return element


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
        normalize: If True, normalize every author with normalize_whitespace(). Defaults to True

    Returns:
        A parsed and striped list of authors
    """

    common_delimiters = [",", ";", " und ", " and ", " & ", r" \| "]

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


def generic_topic_parsing(
    keywords: Optional[Union[str, List[str]]], delimiter: Union[str, List[str]] = ","
) -> List[str]:
    if isinstance(delimiter, str):
        delimiter = [delimiter]

    if not keywords:
        topics = []
    elif isinstance(keywords, str):
        topics = [
            cleaned
            for keyword in re.split(pattern=f"[{''.join(delimiter)}]", string=keywords)
            if (cleaned := keyword.strip())
        ]
    elif isinstance(keywords, list) and all(isinstance(s, str) for s in keywords):
        topics = keywords
    else:
        raise TypeError(f"Encountered unexpected type {type(keywords)} as keyword parameter")

    return list(dict.fromkeys(topics))


_tz_infos = {"CET": 3600, "CEST": 7200, "IST": 19800}


class CustomParserInfo(parser.parserinfo):
    MONTHS = [
        ("Jan", "January", "Januar"),
        ("Feb", "February", "Februar"),
        ("Mar", "March", "März"),
        ("Apr", "April"),
        ("May", "May", "Mai"),
        ("Jun", "June", "Juni"),
        ("Jul", "July", "Juli"),
        ("Aug", "August"),
        ("Sep", "Sept", "September"),
        ("Oct", "October", "Oktober", "Okt"),
        ("Nov", "November"),
        ("Dec", "December", "Dezember", "Dez"),
    ]


def generic_date_parsing(date_str: Optional[str]) -> Optional[datetime]:
    return parser.parse(date_str, tzinfos=_tz_infos, parserinfo=CustomParserInfo(), fuzzy=True) if date_str else None


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


def image_author_parsing(authors: Union[str, List[str]]) -> List[str]:
    credit_keywords = [
        "fotograf",
        "credits?",
        "quellen?",
        "bild(rechte)?",
        "sources?",
        r"(((f|ph)oto(graph)?s?|image|illustrations?|cartoons?|pictures?)\s*)+(by|:|courtesy)",
        "©",
        "– alle rechte vorbehalten",
        "copyright",
        "all rights reserved",
        "courtesy of",
        "＝",
    ]
    author_filter = re.compile(r"(?is)^(" + r"|".join(credit_keywords) + r"):?\s*")

    def clean(author: str):
        author = re.sub(r"^\((.*)\)$", r"\1", author).strip()
        # filtering credit keywords
        author = re.sub(author_filter, "", author, count=1)
        # filtering bloat follwing the author
        author = re.sub(r"(?i)/?copyright.*", "", author)
        return author.strip()

    if isinstance(authors, list):
        authors = [clean(author) for author in authors]
    else:
        authors = clean(authors)
    return generic_author_parsing(authors)


# https://regex101.com/r/MplUXL/2
_srcset_pattern = re.compile(r"(?P<url>\S+)\s*(?P<descriptor>[0-9.]+[wx])?(,?\s*)")


def parse_srcset(srcset: str) -> Dict[str, str]:
    # Updated regular expression to account for query parameters in URLs
    urls = {}
    for match in _srcset_pattern.finditer(srcset.strip()):
        url = match.group("url")
        descriptor = match.group("descriptor")  # Width (w) or pixel density (x)
        urls[descriptor or "1x"] = url
    # return sorted dict based on int value of descriptor
    return dict(sorted(urls.items(), key=lambda item: float(item[0][:-1])))


# that's the same as string(./attribute::*[ends-with(name(), '*')]) but LXML doesn't support the ends-with function
# these two selectors select the value of the first attribute found ending with src/srcset relative to the node
# as truing value
_srcset_selector = XPath(
    "./@*[substring(name(), string-length(name()) - string-length('srcset') + 1)  = 'srcset'][starts-with(., 'http') or starts-with(., '/')]"
)
_src_selector = XPath(
    "./@*[substring(name(), string-length(name()) - string-length('src') + 1)  = 'src'][starts-with(., 'http') or starts-with(., '/')]"
)


def parse_urls(node: lxml.html.HtmlElement) -> Optional[Dict[str, str]]:
    def get_longest_string(strings: List[str]) -> str:
        return sorted(strings, key=len)[-1]

    if srcset := cast(List[str], _srcset_selector(node)):
        return parse_srcset(get_longest_string(srcset))
    elif src := cast(List[str], _src_selector(node)):
        return {"1x": get_longest_string(src)}
    else:
        return None


class _DimensionCalculator:
    def __init__(
        self, width: Optional[float] = None, height: Optional[float] = None, ratio: Optional[float] = None
    ) -> None:
        self.width = width
        self.height = height
        self.ratio = ratio

    def calculate(
        self, width: Optional[float] = None, height: Optional[float] = None, dpr: Optional[float] = None
    ) -> Optional[Dimension]:
        if not (width or height):
            width = self.width
            height = self.height
        if dimension := Dimension.from_ratio(width, height, self.ratio):
            return dimension * (dpr or 1)
        return None


_media_param_pattern = re.compile(r"\(\s*(?P<param>[\w-]+)\s*:\s*(?P<value>[\d./]+)(?P<unit>[a-z]*)\)")
_width_x_height_pattern = re.compile(r"(?P<width>[0-9]+)x(?P<height>[0-9]+)")


def get_versions_from_node(
    source: lxml.html.HtmlElement, ratio: Optional[float], size_pattern: Optional[Pattern[str]]
) -> Set[ImageVersion]:
    if not (urls := parse_urls(source)):
        return set()

    # get min/max width
    query_width = None
    for param, value, descriptor in re.findall(_media_param_pattern, source.get("media", "").split(",")[0]):
        if param in ["min-width", "max-width"]:
            if descriptor != "px":
                logger.debug(f"Pixel calculation not implemented for {descriptor}")
            else:
                # with the assumption that there is only one max/min width per ',' seperated query and only
                # either min- or max-width
                query_width = f"{param}:{value}"

    # get width, height and init calculator
    if (src_width := source.get("width")) and src_width.replace(".", "", 1).isdigit():
        width = float(src_width or 0) or None
    else:
        width = None
    if (src_height := source.get("height")) and src_height.replace(".", "", 1).isdigit():
        height = float(src_height or 0) or None
    else:
        height = None
    if width and height:
        ratio = width / height
    calculator = _DimensionCalculator(width, height, ratio)

    versions = set()
    for descriptor, url in urls.items():
        kwargs: Dict[str, float] = {}
        if descriptor is not None:
            if match := re.search(r"(?P<multiplier>[0-9.]+)x", descriptor):
                kwargs["dpr"] = float(match.group("multiplier"))
            elif match := re.search(r"(?P<width>[0-9]+)(px|w)", descriptor):
                kwargs["width"] = float(match.group("width"))

        if size_pattern is not None and (
            match_dict := _get_match_dict(size_pattern, url, conversion=lambda x: float(x))
        ):
            kwargs.update(match_dict)
        elif not (calculator.width or kwargs.get("width")) and (match := re.search(_width_x_height_pattern, url)):
            kwargs.update({k: float(v) for k, v in match.groupdict().items() if v is not None})

        version = ImageVersion(
            url=url, query_width=query_width, size=calculator.calculate(**kwargs), type=source.get("type")
        )
        versions.add(version)

    return versions


_relative_source_selector = XPath("./ancestor::picture//source")


def parse_versions(img_node: lxml.html.HtmlElement, size_pattern: Optional[Pattern[str]] = None) -> List[ImageVersion]:
    # parse img
    if (
        (default_width := img_node.get("width"))
        and not default_width == "auto"
        and (default_height := img_node.get("height"))
        and not default_height == "auto"
    ):
        ratio = float(default_width) / float(default_height)
    else:
        ratio = None

    versions = set()
    for source in _relative_source_selector(img_node) + [img_node]:
        for version in get_versions_from_node(source, ratio, size_pattern):
            versions.add(version)

    return sorted(versions)


class IndexedImageNode(NamedTuple):
    position: int
    content: lxml.html.HtmlElement
    is_cover: bool


def parse_image_nodes(
    image_nodes: List[IndexedImageNode],
    caption_selector: XPath,
    alt_selector: XPath,
    author_selector: Union[XPath, Pattern[str]],
    domain: Optional[str] = None,
    size_pattern: Optional[Pattern[str]] = None,
) -> Iterator[Image]:
    """Extract urls, caption, description and authors from a list of <img> nodes

    Args:
        image_nodes: Indexed <img> nodes to parse.
        caption_selector: Selector selecting the caption of an image. Defaults to selecting the figcaption element.
        alt_selector: Selector selecting the descriptive text of an image. Defaults to selecting alt value.
        author_selector: Selector selecting the credits for an image. Defaults to selecting an arbitrary child of
            figure with copyright or credit in its class attribute.
        domain: If set, the domain will be prepended to URLs in case they are relative
        size_pattern: Regular expression to select <width>, <height> and <dpr> from the image URL. The given regExp
            will be matched with re.findall and overwrites existing values. Defaults to None.

    Returns:
        List of Images
    """

    def nodes_to_text(nodes: List[Union[lxml.html.HtmlElement, str]]) -> Optional[str]:
        return " ".join(generic_nodes_to_text(nodes, normalize=True)) or None

    for position, node, is_cover in image_nodes:
        # parse URLs
        if not (versions := parse_versions(node, size_pattern)):
            continue

        # resolve relative URLs if domain is given
        if domain is not None:
            for version in versions:
                version.url = urljoin(domain, version.url)

        # parse caption
        caption = nodes_to_text(caption_selector(node))

        # parse description
        description = nodes_to_text(alt_selector(node))

        # parse authors
        authors = []
        if isinstance(author_selector, Pattern):
            # author is part of the caption
            if caption and (match := re.search(author_selector, caption)):
                authors = [match.group("credits")]
                caption = re.sub(author_selector, "", caption).strip() or None
            elif description and (match := re.search(author_selector, description)):
                authors = [match.group("credits")]
        else:
            # author is selectable as node
            if author_nodes := author_selector(node):
                authors = generic_nodes_to_text(author_nodes, normalize=True)
        authors = image_author_parsing(authors)

        yield Image(
            versions=versions,
            caption=caption,
            authors=authors,
            description=description,
            is_cover=is_cover,
            position=position,
        )


class Bounds(NamedTuple):
    upper: int
    first_paragraph: Optional[int]
    lower: int


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


_og_url_selector = XPath("string(//meta[@property='og:url']/@content)")


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
    relative_urls: Union[bool, XPath] = False,
    size_pattern: Pattern[str] = re.compile(
        r"width([=-])(?P<width>[0-9.]+)|height([=-])(?P<height>[0-9.]+)|dpr=(?P<dpr>[0-9.]+|)"
    ),
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
        relative_urls: If True, the extractor assumes that image src URLs are relative and prepends the publisher
            domain
        size_pattern: Regular expression to select <width>, <height> and <dpr> from the image URL. The given regExp
            will be matched with re.findall and overwrites existing values. Defaults to None.

    Returns:
        A list of Images contained within the article

    """

    # index nodes df
    dom = DOM(doc)

    # determine bounds based on df index
    if not (bounds := determine_bounds(dom, paragraph_selector, upper_boundary_selector, lower_boundary_selector)):
        raise ValueError("Bounds could not be determined")

    if relative_urls:
        if isinstance(relative_urls, bool):
            selector = _og_url_selector
        else:
            selector = relative_urls
        if not (domain := selector(dom.root)):
            raise ValueError("Could not determine domain")
    else:
        domain = None

    image_nodes = [
        IndexedImageNode(position=position, content=node, is_cover=position < (bounds.first_paragraph or 0))
        for node in image_selector(doc)
        if bounds.upper < (position := dom.get_index(node)) < bounds.lower
    ]

    images = list(
        parse_image_nodes(
            image_nodes=image_nodes,
            caption_selector=caption_selector,
            alt_selector=alt_selector,
            author_selector=author_selector,
            domain=domain,
            size_pattern=size_pattern,
        )
    )

    return images
