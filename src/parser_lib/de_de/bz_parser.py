import datetime
from typing import Optional, List

import dateutil.parser
import lxml.html

from src.html_parser import BaseParser
from src.html_parser.base_parser import register_attribute
from src.html_parser.utility import strip_nodes_to_text


class BZParser(BaseParser):
    """
    This parser is for the old format!
    """


    @register_attribute
    def plaintext(self) -> Optional[str]:
        doc: lxml.html.HtmlElement = self.cache['doc']
        text_node_selector: str = (
            ".o-article > p"
        )

        if nodes := doc.cssselect(text_node_selector):
            return strip_nodes_to_text(nodes)

    @register_attribute
    def authors(self) -> List[str]:
        author_node_selector = '.ld-author-replace'
        author_nodes = self.cache['doc'].cssselect(author_node_selector)
        return [node.text_content() for node in author_nodes]

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:


        iso_date_str = self.ld().get('datePublished')

        return dateutil.parser.parse(iso_date_str)

    @register_attribute
    def title(self):
        return self.meta().get('og:title')

    @register_attribute
    def topics(self) -> List[str]:
        if keyword_str := self.meta().get('keywords'):
            return keyword_str.split(', ')
