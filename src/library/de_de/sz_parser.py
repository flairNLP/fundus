import datetime
from typing import Optional, List

from src.parser.html_parser import BaseParser, register_attribute
from src.parser.html_parser.utility import generic_plaintext_extraction_with_css, generic_author_parsing, \
    generic_date_parsing, generic_topic_parsing


class SZParser(BaseParser):

    @register_attribute
    def plaintext(self) -> Optional[str]:
        return generic_plaintext_extraction_with_css(self.precomputed.doc,
                                                     'main [itemprop="articleBody"] > p, '
                                                     'main .css-korpch > div > ul > li'
                                                     )

    @register_attribute
    def authors(self) -> List[str]:
        return generic_author_parsing(self.precomputed.ld.bf_search('author'))

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search('datePublished'))

    @register_attribute
    def title(self):
        return self.precomputed.ld.get('headline')

    @register_attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.ld.bf_search('keywords'))
