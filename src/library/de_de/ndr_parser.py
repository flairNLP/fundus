import datetime
from typing import Optional, List

from src.parser.html_parser import BaseParser, register_attribute
from src.parser.html_parser.utility import generic_plaintext_extraction_with_css, generic_author_extraction, \
    generic_date_extraction, generic_topic_extraction


class NDRParser(BaseParser):
    @register_attribute
    def plaintext(self) -> Optional[str]:
        return generic_plaintext_extraction_with_css(self.precomputed.doc,
                                                     ".modulepadding > p"
                                                     )

    @register_attribute
    def authors(self) -> List[str]:
        return generic_author_extraction(self.precomputed.meta, ["author"])

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_extraction(self.precomputed.ld, "datePublished")

    @register_attribute
    def title(self):
        return self.meta().get('title')

    @register_attribute
    def topics(self) -> Optional[List[str]]:
        return generic_topic_extraction(self.precomputed.meta)
