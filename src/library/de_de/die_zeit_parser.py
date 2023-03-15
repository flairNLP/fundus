import datetime
from typing import Optional, List

from src.parser.html_parser import BaseParser, attribute, ArticleBody
from src.parser.html_parser.utility import generic_author_parsing, generic_date_parsing, generic_topic_parsing, \
    extract_article_body_with_selector


class DieZeitParser(BaseParser):

    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(self.precomputed.doc,
                                                  summary_selector='div.summary',
                                                  subhead_selector='div.article-page > h2',
                                                  paragraph_selector='div.article-page > p')

    @attribute
    def authors(self) -> List[str]:
        return generic_author_parsing(self.precomputed.ld.bf_search('author'))

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search('datePublished'))

    @attribute
    def title(self):
        return self.precomputed.ld.bf_search('headline')

    @attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get('keywords'))
