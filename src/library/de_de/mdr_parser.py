import datetime
from typing import Optional, List

from src.parser.html_parser import BaseParser, attribute, ArticleBody
from src.parser.html_parser.utility import (extract_article_body_with_selector, generic_topic_parsing,
                                            generic_date_parsing, generic_text_extraction_with_css)


class MDRParser(BaseParser):

    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(self.precomputed.doc,
                                                  summary_selector='p.einleitung',
                                                  subhead_selector='div > .subtitle',
                                                  paragraph_selector='div.paragraph')

    @attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get('news_keywords'))

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search('datePublished'))

    @attribute
    def authors(self) -> List[str]:
        if author := generic_text_extraction_with_css(self.precomputed.doc, '.articleMeta > .author'):
            cleaned_author = author.replace('von', '').replace(' und ', ', ')
            return [name.strip() for name in cleaned_author.split(',')]
        return []

    @attribute
    def title(self) -> Optional[str]:
        return title if isinstance(title := self.precomputed.ld.bf_search('headline'), str) else None
