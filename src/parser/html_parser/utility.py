import itertools
import re
from copy import copy
from dataclasses import dataclass, field
from datetime import datetime
from functools import total_ordering
from typing import Dict, List, Literal, Optional, Union, cast

import dateutil.tz
import lxml.html
import more_itertools
from dateutil import parser

from src.parser.html_parser.data import ArticleBody, ArticleSection, TextSequence


@total_ordering
@dataclass(eq=False)
class Node:
    position: int
    node: lxml.html.HtmlElement = field(compare=False)
    type: str = field(compare=False)

    def striped(self, chars: Optional[str] = None) -> str:
        return str(self).strip(chars)

    def _get_break_preserved_node(self) -> lxml.html.HtmlElement:
        copied_node = copy(self.node)
        for br in copied_node.xpath("*//br"):
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
        return self._get_break_preserved_node().text_content()


def extract_article_body_with_selector(
    doc: lxml.html.HtmlElement,
    paragraph_selector: str,
    summary_selector: Optional[str] = None,
    subheadline_selector: Optional[str] = None,
    mode: Literal["css", "xpath"] = "css",
) -> ArticleBody:
    # depth first index for each element in tree
    df_idx_by_ref = {element: i for i, element in enumerate(doc.iter())}

    def extract_nodes(selector: str, node_type: str) -> List[Node]:
        if not selector and node_type:
            raise ValueError("Both a selector and node type are required")
        if mode == "css":
            return [Node(df_idx_by_ref[element], element, node_type) for element in doc.cssselect(selector)]
        else:
            return [Node(df_idx_by_ref[element], element, node_type) for element in doc.xpath(selector)]

    summary_nodes = extract_nodes(summary_selector, "S") if summary_selector else []
    subhead_nodes = extract_nodes(subheadline_selector, "H") if subheadline_selector else []
    paragraph_nodes = extract_nodes(paragraph_selector, "P")
    nodes = sorted(summary_nodes + subhead_nodes + paragraph_nodes)

    striped_nodes = [node for node in nodes if node.striped()]

    instructions = more_itertools.split_when(striped_nodes, pred=lambda x, y: x.type != y.type)

    if not summary_nodes:
        instructions = more_itertools.prepend([], instructions)

    if not subhead_nodes or (paragraph_nodes and subhead_nodes[0] > paragraph_nodes[0]):
        first = next(instructions)
        instructions = itertools.chain([first, []], instructions)

    summary = TextSequence(map(lambda x: x.striped("\n"), next(instructions)))
    sections: List[ArticleSection] = []

    for chunk in more_itertools.chunked(instructions, 2):
        if len(chunk) == 1:
            chunk.append([])
        texts = [list(map(lambda x: x.striped("\n"), c)) for c in chunk]
        sections.append(ArticleSection(*map(TextSequence, texts)))

    return ArticleBody(summary=summary, sections=sections)


def get_meta_content(tree: lxml.html.HtmlElement) -> Dict[str, str]:
    meta_node_selector = "meta[name], meta[property]"
    meta_nodes = tree.cssselect(meta_node_selector)
    meta: Dict[str, str] = {}
    for node in meta_nodes:
        key = node.attrib.get("name") or node.attrib.get("property")
        value = node.attrib.get("content")
        if key and value:
            meta[key] = value
    return meta


def strip_nodes_to_text(text_nodes: List[lxml.html.HtmlElement]) -> Optional[str]:
    if not text_nodes:
        return None
    return "\n\n".join(([re.sub(r"\n+", " ", node.text_content()) for node in text_nodes])).strip()


def generic_author_parsing(
    value: Union[
        Optional[str],
        Dict[str, str],
        List[str],
        List[Dict[str, str]],
    ]
) -> List[str]:
    if not value:
        return []

    parameter_type_error: TypeError = TypeError(
        f"<value> '{value}' has an unsupported type {type(value)}. "
        f"Supported types are 'Optional[str], Dict[str, str], List[str], List[Dict[str, str]],'"
    )

    authors: List[str]

    if isinstance(value, str):
        authors = [value]

    elif isinstance(value, dict):
        authors = [name] if (name := value.get("name")) else []

    elif isinstance(value, list):
        if isinstance(value[0], str):
            value = cast(List[str], value)
            authors = value

        elif isinstance(value[0], dict):
            value = cast(List[Dict[str, str]], value)
            authors = [name for author in value if (name := author.get("name"))]

        else:
            raise parameter_type_error

    else:
        raise parameter_type_error

    return [name.strip() for name in authors]


def generic_text_extraction_with_css(doc, selector: str) -> Optional[str]:
    nodes = doc.cssselect(selector)
    return strip_nodes_to_text(nodes)


def generic_topic_parsing(keyword_str: Optional[str], delimiter: str = ",") -> List[str]:
    return [keyword.strip() for keyword in keyword_str.split(delimiter)] if keyword_str else []


_tzs = ["CET", "CEST"]
_tz_infos = {tz: dateutil.tz.gettz(tz) for tz in _tzs}


def generic_date_parsing(date_str: str) -> Optional[datetime]:
    return parser.parse(date_str, tzinfos=_tz_infos) if date_str else None
