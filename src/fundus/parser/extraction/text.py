from __future__ import annotations

import re
from typing import (
    Callable,
    List,
    Match,
    Optional,
    Pattern,
    Sequence,
    Set,
    Union,
)

import lxml.html
from lxml.cssselect import CSSSelector
from lxml.etree import XPath

_space_characters = {
    "whitespace": r"\s",
    "non-breaking-space": r"\u00A0",
    "zero-width-space": r"\u200B",
    "zero-width-non-joiner": r"\u200C",
    "zero-width-joiner": r"\u200D",
    "zero-width-no-break_space": r"\uFEFF",
}
_ws_pattern: Pattern[str] = re.compile(rf"[{''.join(_space_characters.values())}]+")


def normalize_whitespace(text: str) -> str:
    return re.sub(_ws_pattern, " ", text).strip()


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


def apply_result_filter(input_list: List[str], result_filter: Optional[Union[Pattern[str], Set[str]]]) -> List[str]:
    if isinstance(result_filter, Pattern):
        return [topic for topic in dict.fromkeys(input_list) if not re.search(result_filter, topic)]
    else:
        normalized_result_filter = {val.lower() for val in result_filter} if result_filter else set()
        return [
            topic
            for topic in dict.fromkeys(input_list)
            if result_filter is None or topic.lower() not in normalized_result_filter
        ]


def generic_text_extraction_with_css(doc, selector: XPath) -> Optional[str]:
    nodes = selector(doc)
    return strip_nodes_to_text(nodes)


_title_selector = CSSSelector("title")


def parse_title_from_root(root: lxml.html.HtmlElement) -> Optional[str]:
    title_node = _title_selector(root)

    if len(title_node) != 1:
        return None

    return strip_nodes_to_text(title_node)
