import datetime
from typing import Optional, List

from src.parser.html_parser import BaseParser, attribute, ArticleBody
from src.parser.html_parser.utility import generic_date_parsing, extract_article_body_with_selector, \
    generic_author_parsing, generic_topic_parsing


class BerlinerZeitungParser(BaseParser):

    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(self.precomputed.doc,
                                                  summary_selector='div[data-testid=article-header] > p',
                                                  subhead_selector='div[id=articleBody] > p',
                                                  paragraph_selector='div[id=articleBody] > h2')

    @attribute
    def title(self) -> Optional[str]:
        return self.precomputed.meta.get('og:title')

    @attribute
    def authors(self) -> List[str]:
        return generic_author_parsing(self.precomputed.meta.get('author'))

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search('datePublished'))

    @attribute
    def topics(self) -> Optional[List[str]]:
        return generic_topic_parsing(self.precomputed.ld.bf_search('keywords'))
