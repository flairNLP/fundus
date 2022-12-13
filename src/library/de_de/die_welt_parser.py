import datetime
from typing import Optional, List

from src.parser.html_parser import BaseParser, register_attribute
from src.parser.html_parser.utility import generic_plaintext_extraction_with_css, generic_author_extraction,\
    generic_topic_extraction, generic_date_extraction


class DieWeltParser(BaseParser):

    @register_attribute
    def plaintext(self) -> Optional[str]:
        return generic_plaintext_extraction_with_css(self.precomputed.doc, "body .c-summary > div, "
                                                                           "body .c-article-text > p")

    @register_attribute
    def authors(self) -> List[str]:
        return generic_author_extraction(self.precomputed.ld, ["author"])

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_extraction(self.precomputed.ld,)

    @register_attribute
    def title(self):
        return self.precomputed.ld.get('headline')

    @register_attribute
    def topics(self) -> List[str]:
        return generic_topic_extraction(self.precomputed.meta,)
