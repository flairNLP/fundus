import datetime
from typing import Optional, List

from src.parser.html_parser import BaseParser, register_attribute
from src.parser.html_parser.utility import generic_plaintext_extraction_with_css, generic_date_extraction, \
    generic_topic_extraction


class BZParser(BaseParser):
    """
    This parser is for the old format!
    """

    @register_attribute
    def plaintext(self) -> Optional[str]:
        return generic_plaintext_extraction_with_css(self.precomputed.doc,  ".o-article > p")

    @register_attribute
    def authors(self) -> List[str]:
        author_node_selector = '.ld-author-replace'
        author_nodes = self.precomputed.doc.cssselect(author_node_selector)
        return [node.text_content() for node in author_nodes]

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_extraction(self.precomputed.ld, "datePublished")

    @register_attribute
    def title(self):
        return self.meta().get('og:title')

    @register_attribute
    def topics(self) -> List[str]:
        return generic_topic_extraction(self.precomputed.meta)