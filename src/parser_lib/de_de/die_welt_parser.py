import datetime
from typing import Optional, List

import dateutil.parser

from src.html_parser import BaseParser
from src.html_parser.base_parser import register_attribute


class DieWeltParser(BaseParser):

    @register_attribute(attribute_is_mandatory=True)
    def plaintext(self) -> Optional[str]:

        return self.generic_plaintext_extraction("body .c-summary > div, "
                                                 "body .c-article-text > p")

    @register_attribute(attribute_is_mandatory=True)
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
