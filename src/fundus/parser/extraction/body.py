from __future__ import annotations

import itertools
import re
from copy import copy
from dataclasses import dataclass, field
from functools import total_ordering
from typing import (
    ClassVar,
    List,
    Optional,
    Type,
)

import lxml.html
import more_itertools
from lxml.etree import XPath

from fundus.parser.extraction.text import normalize_whitespace
from fundus.parser.types.body import ArticleBody, ArticleSection, TextSequence


@total_ordering
@dataclass(eq=False)
class Node:
    position: int
    node: lxml.html.HtmlElement = field(compare=False)
    _break_selector: ClassVar[XPath] = XPath("*//br")

    # one could replace this recursion with XPath using an expression like this:
    # //*[not(self::script) and text()]/text(), but for whatever reason, that's actually 50-150% slower
    # than simply using the implemented mixture below
    def text_content(self, excluded_tags: Optional[List[str]] = None, tag_filter: Optional[XPath] = None) -> str:
        guarded_excluded_tags: List[str] = excluded_tags or []

        def _text_content(element: lxml.html.HtmlElement) -> str:
            if (
                element.tag in guarded_excluded_tags
                or isinstance(element, lxml.html.HtmlComment)
                or (tag_filter and tag_filter(element))
            ):
                return element.tail or ""
            text = element.text or ""
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
    tag_filter: Optional[XPath] = None,
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

    # data-cleaning:
    def _cond(node: lxml.html.HtmlElement) -> bool:
        def has_normalized_text():
            return bool(node.xpath("normalize-space(text())"))

        def has_em_child():
            return bool(node.xpath("./em"))

        return not has_normalized_text() and has_em_child()

    while paragraph_nodes and _cond(paragraph_nodes[-1].node):
        paragraph_nodes.pop()

    nodes = sorted(summary_nodes + subhead_nodes + paragraph_nodes)

    if not nodes:
        # return empty body if no text is present
        return ArticleBody(TextSequence([]), [])

    instructions = more_itertools.split_when(nodes, pred=lambda x, y: type(x) is not type(y))

    if not summary_nodes:
        instructions = more_itertools.prepend([], instructions)
    elif not nodes[: len(summary_nodes)] == summary_nodes:
        raise ValueError("All summary nodes should be at the beginning of the article")

    if not subhead_nodes or (paragraph_nodes and subhead_nodes[0] > paragraph_nodes[0]):
        first = next(instructions)
        instructions = itertools.chain([first, []], instructions)

    summary = TextSequence(
        map(
            lambda x: normalize_whitespace(x.text_content(excluded_tags=["script"], tag_filter=tag_filter)),
            next(instructions),
        )
    )
    sections: List[ArticleSection] = []

    for chunk in more_itertools.chunked(instructions, 2):
        if len(chunk) == 1:
            chunk.append([])
        texts = [
            list(
                map(lambda x: normalize_whitespace(x.text_content(excluded_tags=["script"], tag_filter=tag_filter)), c)
            )
            for c in chunk
        ]
        sections.append(ArticleSection(*map(TextSequence, texts)))

    return ArticleBody(summary=summary, sections=sections)


def transform_breaks_to_tag(
    element: lxml.html.HtmlElement, tag: str = "p", replace: bool = False, **attribs: str
) -> None:
    """Splits the content of <element> on <br> tags into paragraphs and wraps them in <tag> elements.

    If <element> is replaced, the previous attributes are attached to the new elements.
    If <element> is not replaced, the wrapped paragraphs are attached to the cleared element.

    Args:
        element: The element on which to perform the transformation.
        tag: The tag to wrap the paragraphs in.
        replace: If True, replace <element> with wrapped paragraphs, else adds them to <element>.
        **attribs: The attributes of the wrapped paragraphs as keyword arguments. I.e. the
            default {"class": "br-wrap"} wil produce the following elements: <p class='br-wrap'>.
            To use python keywords wrap them dunder scores. __class__ for class.
    """

    if attribs:
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
        return None

    wrapped_paragraphs = [f"<{tag}{' ' + generate_attrs()}>{paragraph}</{tag}>" for paragraph in paragraphs]

    if replace:
        if (parent := element.getparent()) is None:
            raise NotImplementedError("Cannot replace elements without parent element")

        previous_attrs = element.attrib
        previous_index = parent.index(element)
        parent.remove(element)
        for new_index, paragraph in enumerate(wrapped_paragraphs, previous_index):
            new_paragraph = lxml.html.fromstring(paragraph)
            new_paragraph.attrib.update(previous_attrs)
            parent.insert(new_index, new_paragraph)
    else:
        # remove children, tail and text from element
        clear_element()

        # add paragraphs to cleared element
        for paragraph in wrapped_paragraphs:
            element.append(lxml.html.fromstring(paragraph))

    return None
