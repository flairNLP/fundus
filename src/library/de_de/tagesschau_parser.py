import datetime
import re
from typing import Optional, List

from src.parser.html_parser import BaseParser, attribute, ArticleBody
from src.parser.html_parser.utility import extract_article_body_with_selector, generic_author_parsing, \
    generic_date_parsing


class TagesschauParser(BaseParser):

    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(self.precomputed.doc,
                                                  summary_selector='//article/p[1]',
                                                  subhead_selector='//article/h2',
                                                  paragraph_selector='//article/p[position() > 1]',
                                                  mode='xpath')

    @attribute
    def authors(self) -> List[str]:
        if raw_author_string := self.precomputed.doc.xpath('string(//div[contains(@class, "authorline__author")])'):
            cleaned_author_string = re.sub(r'^Von |, ARD[^\s,]*', '', raw_author_string)
            return generic_author_parsing(cleaned_author_string)
        else:
            return []

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search('datePublished'))

    @attribute
    def title(self):
        return self.precomputed.meta.get('og:title')

    @attribute
    def topics(self) -> List[str]:
        topic_nodes = self.precomputed.doc.cssselect('div.meldungsfooter .taglist a')
        return [node.text_content() for node in topic_nodes]
