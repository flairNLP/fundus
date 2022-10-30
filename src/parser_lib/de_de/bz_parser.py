import datetime
from typing import Optional, List

import dateutil.parser

from src.html_parser import BaseParser
from src.html_parser.base_parser import register_attribute


class BZParser(BaseParser):
    """
    This parser is for the old format!
    """

    @register_attribute
    def plaintext(self) -> Optional[str]:
        return self.generic_plaintext_extraction(".o-article > p")

    @register_attribute
    def authors(self) -> List[str]:
        author_node_selector = '.ld-author-replace'
        author_nodes = self.cache['doc'].cssselect(author_node_selector)
        return [node.text_content() for node in author_nodes]

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:

        iso_date_str = self.ld().get('datePublished')
        if iso_date_str:
            return dateutil.parser.parse(iso_date_str)
        return None

    @register_attribute
    def title(self):
        return self.meta().get('og:title')

    @register_attribute
    def topics(self) -> List[str]:
        if keyword_str := self.meta().get('keywords'):
            return keyword_str.split(', ')
