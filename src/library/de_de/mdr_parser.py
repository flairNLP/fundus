import datetime
from typing import Optional, List

from src.parser.html_parser import register_attribute, BaseParser
from src.parser.html_parser.utility import generic_date_extraction, generic_topic_extraction, \
    generic_plaintext_extraction_with_css, generic_author_extraction


class MDRParser(BaseParser):

    @register_attribute(priority=4)
    def plaintext(self) -> Optional[str]:
        return generic_plaintext_extraction_with_css(self.precomputed.doc, 'div.paragraph')

    @register_attribute
    def topics(self) -> Optional[List[str]]:
        return generic_topic_extraction(self.precomputed.meta)

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_extraction(self.precomputed.ld)

    @register_attribute
    def authors(self) -> Optional[List[str]]:
        return generic_author_extraction(self.meta(), ['author'])

    @register_attribute(priority=4)
    def title(self) -> Optional[str]:
        return self.meta().get('og:title')
