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
    List,
    Match,
    Optional,
    Pattern,
    Type,
    Union,
)

import lxml.html
import more_itertools
from dateutil import parser
from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.logging import create_logger
from fundus.parser.data import (
    ArticleBody,
    ArticleSection,
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


def generic_nodes_to_text(nodes: List[lxml.html.HtmlElement], normalize: bool = False) -> List[str]:
    if not nodes:
        return []
    texts = [
        normalize_whitespace(str(node.text_content())) if normalize else str(node.text_content()) for node in nodes
    ]
    return [text for text in texts if text]


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

    with common delimiters := [",", ";", " und ", " and ", " & "]

    All values are stripped with default strip() method before returned.

    Args:
        value:      An input value representing author(s) which get parsed based on type
        split_on:   Only relevant for type(<value>) = str. If set, split <value> on <split_on>,
            else (default) split <value> on common delimiters

    Returns:
        A parsed and striped list of authors
    """

    common_delimiters = [",", ";", " und ", " and ", " & "]

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
