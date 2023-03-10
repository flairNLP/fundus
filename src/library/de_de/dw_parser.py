import datetime
from typing import Optional, List

from src.parser.html_parser import BaseParser, register_attribute, ArticleBody
from src.parser.html_parser.utility import  generic_author_parsing, \
    generic_date_parsing, generic_topic_parsing, generic_text_extraction_with_css, extract_article_body_with_selector


class DWParser(BaseParser):

    @register_attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(self.precomputed.doc,
                                             summary_selector='p.intro',
                                             subhead_selector='div.longText > p',
                                             paragraph_selector='div.longText > h2')

    @register_attribute
    def authors(self) -> List[str]:
        raw_author_string: str = self.precomputed.doc.xpath(
            "normalize-space(" '//ul[@class="smallList"]' '/li[strong[contains(text(), "Auto")]]' "/text()[last()]" ")"
        )
        return generic_author_parsing(raw_author_string)

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        raw_date_str: str = self.precomputed.doc.xpath(
            "normalize-space(" '//ul[@class="smallList"]' '/li[strong[contains(text(), "Datum")]]' "/text())"
        )
        return generic_date_parsing(raw_date_str)

    @register_attribute
    def title(self):
        return generic_text_extraction_with_css(self.precomputed.doc, '.col3 h1')

    @register_attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get('keywords'))
