import re
from typing import Dict, List, Optional

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
