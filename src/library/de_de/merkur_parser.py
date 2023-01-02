import datetime
from typing import Optional, List

from src.parser.html_parser import BaseParser, register_attribute
from src.parser.html_parser.utility import generic_plaintext_extraction_with_css, generic_author_extraction, \
    generic_date_extraction, generic_article_id_extraction_from_url


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
        return generic_date_extraction(self.precomputed.ld["mainEntity"])

    @register_attribute
    def title(self):
        return self.meta().get('og:title')

    @register_attribute
    def article_id(self):
        return generic_article_id_extraction_from_url(self.precomputed.meta["og:url"],
                                                      "(?:merkur.de/).*(?:-)(?P<id_group>[0-9]{8})(?:.html)")
