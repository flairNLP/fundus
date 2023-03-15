from datetime import datetime
from typing import List, Optional

from src.parser.html_parser import BaseParser, ArticleBody, register_attribute
from src.parser.html_parser.utility import extract_article_body_with_selector, generic_author_parsing, \
    generic_date_parsing


class SPONParser(BaseParser):
    @register_attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(self.precomputed.doc,
                                                  summary_selector='header .leading-loose',
                                                  subheadline_selector='main .word-wrap > h3',
                                                  paragraph_selector='main .word-wrap > p')

    @register_attribute
    def authors(self) -> List[str]:
        return generic_author_parsing(self.precomputed.ld.bf_search("author"))

    @register_attribute
    def publishing_date(self) -> Optional[datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

    @register_attribute
    def title(self) -> Optional[str]:
        return self.precomputed.meta.get('og:title')
