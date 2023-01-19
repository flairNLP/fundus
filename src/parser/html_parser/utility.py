import re
from datetime import datetime
from typing import Any, Union, Dict, List, Optional

import dateutil
import lxml.html

from src.custom_types.structural_typing import HasGet


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


def generic_author_parsing(value: Union[str, dict, List[dict]]) -> Optional[List[str]]:
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