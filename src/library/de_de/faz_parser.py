import datetime
from typing import Optional, List

from src.parser.html_parser import BaseParser, register_attribute
from src.parser.html_parser.utility import generic_plaintext_extraction_with_css, generic_date_parsing, \
    generic_author_parsing, generic_topic_parsing


class FAZParser(BaseParser):

    @register_attribute
    def plaintext(self) -> Optional[str]:
        return generic_plaintext_extraction_with_css(self.precomputed.doc, 'div.atc-Text > p')

    @register_attribute
    def topics(self) -> Optional[List[str]]:
        return generic_topic_parsing(self.precomputed.meta.get('keywords'))

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search('datePublished'))

    @register_attribute
    def authors(self) -> List[str]:
        return generic_author_parsing(self.precomputed.meta.get('author'))

    @register_attribute
    def title(self) -> Optional[str]:
        return self.precomputed.meta.get('og:title')
