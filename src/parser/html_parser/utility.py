import re
from datetime import datetime
from typing import Dict, List, Optional, Any

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


def generic_author_extraction(source: HasGet, key_list: List[str]) -> List[str]:
    authors = _get_nested_value_with_key_path_as_list(source, key_list)

    if not authors:
        return []

    if isinstance(authors, str):
        authors = [authors]

    elif isinstance(authors, list):
        authors = [name for author in authors if (name := author.get('name'))]

    elif isinstance(authors, dict):
        authors = [name] if (name := authors.get('name')) else []

    else:
        raise TypeError(f"Value '{authors}' in 'source' dict with key path '{' -> '.join(key_list)}' has an unsupported"
                        f"type. Supported types are 'str, list, dict'")

    return authors


def generic_plaintext_extraction_with_css(doc, selector: str) -> Optional[str]:
    nodes = doc.cssselect(selector)
    return strip_nodes_to_text(nodes)


def generic_topic_extraction(meta: Dict[str, any], key_word: str = "keywords", delimiter: str = ',') -> List[str]:
    if keyword_str := meta.get(key_word):
        return [keyword.strip() for keyword in keyword_str.split(delimiter)]
    return []


def generic_date_extraction(meta, key_word: str = "datePublished") -> Optional[datetime]:
    if date_str := meta.get(key_word):
        return dateutil.parser.parse(date_str)
    return None
