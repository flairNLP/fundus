import datetime
from typing import Optional, List

import dateutil.parser
import lxml.html

from src.html_parser import BaseParser
from src.html_parser.base_parser import register_attribute
from src.html_parser.utility import strip_nodes_to_text
from stream.utils import listify


class DieWeltParser(BaseParser):

    @register_attribute
    def plaintext(self) -> Optional[str]:

        return self.
        doc: lxml.html.HtmlElement = self.cache['doc']
        selector: str = (
            "body .c-summary > div, "
            "body .c-article-text > p"
        )
        if nodes := doc.cssselect(selector):
            return strip_nodes_to_text(nodes)

    @register_attribute
    def authors(self) -> List[str]:
        return self.generic_author_extraction(self.ld(), ["author"])

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        if iso_date_str := self.ld().get('datePublished'):
            return dateutil.parser.parse(iso_date_str)

    @register_attribute
    def title(self):
        return self.ld().get('headline')

    @register_attribute
    def topics(self) -> List[str]:
        if keyword_str := self.meta().get('keywords'):
            return keyword_str.split(', ')
