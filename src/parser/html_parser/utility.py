import re
from datetime import datetime
from typing import Dict, List, Optional

import dateutil
import lxml.html


def get_meta_content(tree: lxml.html.HtmlElement) -> Dict[str, str]:
    meta_node_selector = 'head > meta[name], head > meta[property]'
    meta_nodes = tree.cssselect(meta_node_selector)
    return {node.attrib.get('name') or node.attrib.get('property'): node.attrib.get('content')
            for node in meta_nodes}


def strip_nodes_to_text(text_nodes: List) -> Optional[str]:
    if not text_nodes:
        return None
    return "\n\n".join(([re.sub(r'\n+', ' ', node.text_content()) for node in text_nodes])).strip()


def generic_author_extraction(source: Dict[str, any], key_list: List[str]) -> Optional[List[str]]:
    current_dict = source
    for key in key_list:
        current_dict = current_dict.get(key, {})

    authors = current_dict

    if isinstance(authors, str):
        return [authors]

    if isinstance(authors, list):
        authors = [author.get('name') for author in authors]
    else:
        authors = [authors.get('name')]
    return authors


def generic_plaintext_extraction_with_css(doc, selector: str) -> Optional[str]:
    nodes = doc.cssselect(selector)
    return strip_nodes_to_text(nodes)


def generic_topic_extraction(base_dict, key_word: str = "keywords") -> List[str]:
    if keyword_str := base_dict.get(key_word):
        return [e.strip(" ") for e in keyword_str.split(",")]
    return []


def generic_date_extraction(base_dict, key_word: str = "datePublished") -> Optional[datetime]:
    if date_str := base_dict.get(key_word):
        return dateutil.parser.parse(date_str)
    return None