import datetime
from typing import Optional, List

from src.parser.html_parser import BaseParser, register_attribute
from src.parser.html_parser.utility import generic_plaintext_extraction_with_css, generic_author_parsing, \
    generic_date_parsing


class MerkurParser(BaseParser):

    @register_attribute
    def plaintext(self) -> Optional[str]:
        return generic_plaintext_extraction_with_css(self.precomputed.doc,
                                                     "p.id-StoryElement-paragraph"
                                                     )

    @register_attribute
    def authors(self) -> Optional[List[str]]:
        return generic_author_parsing(self.precomputed.ld.bf_search("author"))

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

    @register_attribute
    def title(self) -> Optional[str]:
        return self.precomputed.meta.get('og:title')
