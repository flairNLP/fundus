import datetime
from typing import Optional, List

import dateutil.parser

from src.parser.html_parser import BaseParser, register_attribute
from src.parser.html_parser.utility import strip_nodes_to_text


class MDRParser(BaseParser):

    @register_attribute(priority=4)
    def plaintext(self) -> Optional[str]:
        return self.generic_plaintext_extraction_with_css('div.paragraph')

    @register_attribute
    def topics(self) -> Optional[List[str]]:
        return self.generic_topic_extraction()

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        if date_string := self.ld().get('datePublished'):
            return dateutil.parser.parse(date_string)

    @register_attribute
    def authors(self) -> str:
        return self.generic_author_extraction(self.meta(), ['author'])

    @register_attribute(priority=4)
    def title(self) -> Optional[str]:
        return self.meta().get('og:title')
