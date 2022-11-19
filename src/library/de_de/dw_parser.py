import datetime
from typing import Optional, List

import dateutil.parser

from src.parser.html_parser import BaseParser, register_attribute
from src.parser.html_parser.utility import generic_plaintext_extraction_with_css, generic_topic_extraction


class DWParser(BaseParser):

    @register_attribute
    def plaintext(self) -> Optional[str]:
        return generic_plaintext_extraction_with_css(self.precomputed.doc, ".longText > p")

    @register_attribute
    def authors(self) -> List[str]:
        raw_str = self.cache['doc'].xpath('normalize-space('
                                          '//ul[@class="smallList"]'
                                          '/li[strong[contains(text(), "Auto")]]'
                                          '/text()[last()]'
                                          ')')
        if raw_str:
            return raw_str.split(', ')
        return []

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        raw_data_str = self.cache['doc'].xpath('normalize-space('
                                               '//ul[@class="smallList"]'
                                               '/li[strong[contains(text(), "Datum")]]'
                                               '/text())')
        return dateutil.parser.parse(raw_data_str)

    @register_attribute
    def title(self):
        return self.meta().get('og:title')

    @register_attribute
    def topics(self) -> List[str]:
        return generic_topic_extraction(self.precomputed.meta)
