from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict

import lxml.html
from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser.extraction.metadata import extract_json_from_dom
from fundus.parser.linked_data import LinkedDataMapping


@dataclass
class Precomputed:
    html: str
    doc: lxml.html.HtmlElement
    meta: Dict[str, str]
    ld: LinkedDataMapping
    cache: Dict[str, Any] = field(default_factory=dict)


_ld_node_selector = XPath("//script[@type='application/ld+json']")


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


_meta_node_selector = CSSSelector("head > meta, body > meta, article > meta")


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
