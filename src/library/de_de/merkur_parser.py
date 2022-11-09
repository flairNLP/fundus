import datetime
from typing import Optional, List

from dateutil import parser

from src.html_parser import BaseParser
from src.html_parser.base_parser import register_attribute


class MerkurParser(BaseParser):


    @register_attribute
    def plaintext(self) -> Optional[str]:
        return self.generic_plaintext_extraction_with_css(
            "p.id-StoryElement-leadText ,"
            "p.id-StoryElement-summary ,"
            "p.id-StoryElement-leadText ,"
            "p.id-StoryElement-paragraph"
        )

    @register_attribute
    def authors(self) -> List[str]:
        return self.generic_author_extraction(self.ld(), ["mainEntity", "author"])

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        current_ld = self.ld().get('mainEntity')
        if current_ld:
            iso_date_str = current_ld.get('datePublished')
        else:
            return None
        if iso_date_str:
            return parser.parse(iso_date_str)
        return None

    @register_attribute
    def title(self):
        return self.meta().get('og:title')
