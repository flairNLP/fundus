import itertools
import re
from copy import copy
from dataclasses import dataclass, field
from datetime import datetime
from functools import total_ordering
from typing import Union, Dict, List, Optional

import lxml.html
import more_itertools
from dateutil import parser

from src.parser.html_parser.data import ArticleBody, ArticleSection, TextSequence


@total_ordering
@dataclass
class Node:
    position: int
    node: lxml.html.HtmlElement = field(compare=False)
    type: str = field(compare=False)

    def striped(self, chars: str = '') -> str:
        return str(self).strip(chars)

    def _get_break_preserved_node(self) -> lxml.html.HtmlElement:
        copied_node = copy(self.node)
        for br in copied_node.xpath('*//br'):
            br.tail = "\n" + br.tail if br.tail else "\n"
        return copied_node

    def __eq__(self, other: 'Node') -> bool:
        return self.position == other.position

    def __lt__(self, other: 'Node') -> bool:
        return self.position < other.position

    def __hash__(self) -> int:
        return hash(self.position)

    def __str__(self) -> str:
        return self._get_break_preserved_node().text_content()


def extract_article_body_with_css(doc: lxml.html.HtmlElement,
                                  paragraph_selector: str,
                                  summary_selector: str = None,
                                  subhead_selector: str = None) -> ArticleBody:
    # depth first index for each element in tree
    df_idx_by_ref = {element: i for i, element in enumerate(doc.iter())}

    def extract_nodes(selector: str, node_type: str) -> List[Node]:
        if not selector and node_type:
            raise ValueError("Both a selector and node type are required")
        raw_nodes = [Node(df_idx_by_ref.get(element), element, node_type) for element in doc.cssselect(selector)]
        return [node for node in raw_nodes if node.striped(chars=' \n ')]

    summary_nodes = extract_nodes(summary_selector, 'S') if summary_selector else []
    subhead_nodes = extract_nodes(subhead_selector, 'H') if subhead_selector else []
    paragraph_nodes = extract_nodes(paragraph_selector, 'P')
    nodes = sorted(summary_nodes + subhead_nodes + paragraph_nodes)

    striped_nodes = [node for node in nodes if str(node)]

    instructions = more_itertools.split_when(striped_nodes, pred=lambda x, y: x.type != y.type)

    if not summary_nodes:
        instructions = more_itertools.prepend([], instructions)

    if (subhead_nodes and paragraph_nodes) and subhead_nodes[0] > paragraph_nodes[0]:
        first = next(instructions)
        instructions = itertools.chain([first, []], instructions)

    kwargs = {'summary': TextSequence(map(lambda x: x.striped('\n'), next(instructions))), 'sections': []}

    for chunk in more_itertools.chunked(instructions, 2):
        if len(chunk) == 1:
            chunk.append([])
        chunk = [list(map(lambda x: x.striped('\n'), c)) for c in chunk]
        kwargs['sections'].append(ArticleSection(*map(TextSequence, chunk)))

    return ArticleBody(**kwargs)


def get_meta_content(tree: lxml.html.HtmlElement) -> Dict[str, str]:
    meta_node_selector = 'head > meta[name], head > meta[property]'
    meta_nodes = tree.cssselect(meta_node_selector)
    return {node.attrib.get('name') or node.attrib.get('property'): node.attrib.get('content')
            for node in meta_nodes}


def strip_nodes_to_text(text_nodes: List) -> Optional[str]:
    if not text_nodes:
        return None
    return "\n\n".join(([re.sub(r'\n+', ' ', node.text_content()) for node in text_nodes])).strip()


def generic_author_parsing(value: Union[str, dict, List[dict]]) -> List[str]:
    if not value:
        return []

    if isinstance(value, str):
        authors = [value]

    elif isinstance(value, list):
        authors = [name for author in value if (name := author.get('name'))]

    elif isinstance(value, dict):
        authors = [name] if (name := value.get('name')) else []

    else:
        raise TypeError(f"<value> '{value}' has an unsupported type {type(value)}. "
                        f"Supported types are 'str, dict, List[dict]'")

    return [name.strip() for name in authors]


def generic_text_extraction_with_css(doc, selector: str) -> Optional[str]:
    nodes = doc.cssselect(selector)
    return strip_nodes_to_text(nodes)


def generic_topic_parsing(keyword_str: str, delimiter: str = ',') -> List[str]:
    return [keyword.strip() for keyword in keyword_str.split(delimiter)] if keyword_str else []


def generic_date_parsing(date_str: str) -> Optional[datetime]:
    return parser.parse(date_str) if date_str else None
