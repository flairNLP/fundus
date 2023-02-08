import datetime
from typing import Optional, List

from src.parser.html_parser import BaseParser, register_attribute
from src.parser.html_parser.utility import (generic_plaintext_extraction_with_css, generic_topic_parsing,
                                            generic_date_parsing)


class MDRParser(BaseParser):

    @register_attribute
    def plaintext(self) -> Optional[str]:
        return generic_plaintext_extraction_with_css(self.precomputed.doc, 'div.paragraph')

    @register_attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get('news_keywords'))

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search('datePublished'))

    @register_attribute
    def authors(self) -> List[str]:
        if author := generic_plaintext_extraction_with_css(self.precomputed.doc, '.articleMeta > .author'):
            cleaned_author = author.replace('von', '').replace(' und ', ', ')
            return [name.strip() for name in cleaned_author.split(',')]
        return []

    @register_attribute
    def title(self) -> Optional[str]:
        return self.precomputed.ld.bf_search('headline')
