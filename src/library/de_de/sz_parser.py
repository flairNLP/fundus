import datetime
from typing import Optional, List

from src.parser.html_parser import BaseParser, register_attribute, ArticleBody
from src.parser.html_parser.utility import extract_article_body_with_selector, generic_author_parsing, \
    generic_date_parsing, generic_topic_parsing


class SZParser(BaseParser):

    @register_attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(self.precomputed.doc,
                                                  summary_selector='main [data-manual="teaserText"]',
                                                  subhead_selector='main [itemprop="articleBody"] > h3',
                                                  paragraph_selector='main [itemprop="articleBody"] > p, '
                                                                     'main .css-korpch > div > ul > li')

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
