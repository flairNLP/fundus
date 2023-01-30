import re
from dataclasses import dataclass, field
from datetime import datetime
from functools import total_ordering
from typing import Any, Union, Tuple
from typing import Dict, List, Optional

import dateutil
import lxml.html
import more_itertools

from src.custom_types.structural_typing import HasGet
from src.parser.html_parser.data import ArticleBody


@total_ordering
@dataclass
class Node:
    position: int
    node: lxml.html.HtmlElement = field(compare=False)
    type: str = field(compare=False)

    def __eq__(self, other: 'Node') -> bool:
        return self.position == other.position

    def __lt__(self, other: 'Node') -> bool:
        return self.position < other.position

    def __hash__(self) -> int:
        return hash(self.position)

    def __str__(self) -> str:
        return self.node.text_content()

    def __repr__(self) -> Tuple[int, hex, str]:
        return self.position, hex(id(self)), self.type


def extract_article_body_with_css(doc: lxml.html.HtmlElement,
                                  meta: dict,
                                  paragraph_selector: str,
                                  summary_selector: str = None,
                                  subhead_selector: str = None) -> ArticleBody:
    # depth first index for each element in tree
    df_idx_by_ref = {element: i for i, element in enumerate(doc.iter())}

    def extract_nodes(selector: str, node_type: str) -> List[Node]:
        if not selector and node_type:
            raise ValueError("Both a selector and node type are required")
        return [Node(df_idx_by_ref.get(element), element, node_type) for element in doc.cssselect(selector)]

    summary_nodes = extract_nodes(summary_selector, 'S') if summary_selector else []
    subhead_nodes = extract_nodes(subhead_selector, 'H') if subhead_selector else []
    paragraph_nodes = extract_nodes(paragraph_selector, 'P')
    nodes = sorted(summary_nodes + subhead_nodes + paragraph_nodes)

    instructions = more_itertools.split_when(nodes, pred=lambda x, y: x.type != y.type)

    # if not summary_nodes:
    #     instructions = more_itertools.prepend([], instructions)

    if subhead_nodes[0] > paragraph_nodes[0]:
        instructions = more_itertools.prepend([], instructions)

    return ArticleBody.from_instructions(instructions)


def _get_nested_value_with_key_path_as_list(source: HasGet, key_list: List[str]) -> Any:
    visited = []
    cur = source
    for key in key_list:
        if not isinstance(cur, HasGet):
            raise TypeError(f"Key path '{' -> '.join(visited)}' leads to an unsupported value in between. Only objects"
                            f" who implement a get method are allowed.")
        cur = cur.get(key)
        visited.append(key)
    return cur


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


def generic_plaintext_extraction_with_css(doc, selector: str) -> Optional[str]:
    nodes = doc.cssselect(selector)
    return strip_nodes_to_text(nodes)


def generic_topic_parsing(keyword_str: str, delimiter: str = ',') -> List[str]:
    return [keyword.strip() for keyword in keyword_str.split(delimiter)] if keyword_str else []


def generic_date_parsing(date_str: str) -> Optional[datetime]:
    return dateutil.parser.parse(date_str) if date_str else None
