import datetime
from typing import Optional, List

from src.parser.html_parser import BaseParser, attribute, ArticleBody
from src.parser.html_parser.utility import extract_article_body_with_selector, generic_date_parsing, \
    generic_author_parsing, generic_topic_parsing


class FAZParser(BaseParser):

    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(self.precomputed.doc,
                                                  summary_selector='div.atc-Intro > p',
                                                  subhead_selector='div.atc-Text > h3',
                                                  paragraph_selector='div.atc-Text > p')

    @attribute
    def topics(self) -> Optional[List[str]]:
        return generic_topic_parsing(self.precomputed.meta.get('keywords'))

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search('datePublished'))

    @attribute
    def authors(self) -> List[str]:
        return generic_author_parsing(self.precomputed.meta.get('author'))

    @attribute
    def title(self) -> Optional[str]:
        return self.precomputed.meta.get('og:title')
