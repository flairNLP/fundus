import datetime
from typing import Optional, List

from src.parser.html_parser import BaseParser, register_attribute
from src.parser.html_parser.utility import generic_plaintext_extraction_with_css, generic_author_extraction, \
    generic_date_extraction, generic_article_id_extraction_from_url


class OrfParser(BaseParser):

    @register_attribute
    def plaintext(self) -> Optional[str]:
        return generic_plaintext_extraction_with_css(self.precomputed.doc,
                                                     "div.story-story > p:not(.caption.tvthek.stripe-credits)")

    @register_attribute
    def authors(self) -> List[str]:
        return generic_author_extraction(self.precomputed.ld, ["author"])

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_extraction(self.precomputed.ld)

    @register_attribute
    def title(self):
        return self.precomputed.meta.get('og:title')

    @register_attribute
    def article_id(self):
        return generic_article_id_extraction_from_url(self.precomputed.meta["og:url"],
                                                      "(?:orf.at/stories/)(?P<id_group>[0-9]{7})")
