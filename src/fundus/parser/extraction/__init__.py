"""The helpers parser versions build their attributes with, gathered from the modules they live in."""

from .body import extract_article_body_with_selector, transform_breaks_to_tag
from .images import image_extraction
from .metadata import (
    extract_json_from_dom,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    parse_json,
)
from .text import (
    apply_substitution_pattern_over_list,
    generic_nodes_to_text,
    generic_text_extraction_with_css,
    normalize_whitespace,
    parse_title_from_root,
    strip_nodes_to_text,
)

__all__ = [
    "apply_substitution_pattern_over_list",
    "extract_article_body_with_selector",
    "extract_json_from_dom",
    "generic_author_parsing",
    "generic_date_parsing",
    "generic_nodes_to_text",
    "generic_text_extraction_with_css",
    "generic_topic_parsing",
    "image_extraction",
    "normalize_whitespace",
    "parse_json",
    "parse_title_from_root",
    "strip_nodes_to_text",
    "transform_breaks_to_tag",
]
