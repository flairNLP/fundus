import datetime
from typing import Optional, List

import dateutil.parser

from src.html_parser import BaseParser
from src.html_parser.base_parser import register_attribute
from src.html_parser.utility import extract_plaintext_from_css_selector


class DWParser(BaseParser):

    @register_attribute
    def plaintext(self) -> Optional[str]:
        return extract_plaintext_from_css_selector(self.cache['doc'], ".longText > p")

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
        if keyword_str := self.meta().get('keywords'):
            return keyword_str.split(', ')
