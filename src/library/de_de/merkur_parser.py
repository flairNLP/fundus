import datetime
from typing import Optional, List

from dateutil import parser

from src.parser.html_parser import BaseParser, register_attribute
from src.parser.html_parser.utility import generic_plaintext_extraction_with_css, generic_author_extraction


class MerkurParser(BaseParser):

    @register_attribute
    def plaintext(self) -> Optional[str]:
        return generic_plaintext_extraction_with_css(self.precomputed.doc,
                                                     "p.id-StoryElement-leadText ,"
                                                     "p.id-StoryElement-summary ,"
                                                     "p.id-StoryElement-leadText ,"
                                                     "p.id-StoryElement-paragraph"
                                                     )

    @register_attribute
    def authors(self) -> List[str]:
        return generic_author_extraction(self.precomputed.ld, ["mainEntity", "author"])

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
