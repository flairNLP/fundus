import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from src.parser.html_parser import ArticleBody, BaseParser, attribute
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_text_extraction_with_css,
    generic_topic_parsing,
)


class DWParser(BaseParser):
    _paragraph_selector = CSSSelector("div.longText > p")
    _summary_selector = CSSSelector("p.intro")
    _subheadline_selector = CSSSelector("div.longText > h2")
    _title_selector =CSSSelector(".col3 h1")

    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            summary_selector=self._summary_selector,
            subheadline_selector=self._subheadline_selector,
            paragraph_selector=self._paragraph_selector,
        )

    @attribute
    def authors(self) -> List[str]:
        raw_author_string: str = self.precomputed.doc.xpath(
            "normalize-space(" '//ul[@class="smallList"]' '/li[strong[contains(text(), "Auto")]]' "/text()[last()]" ")"
        )
        return generic_author_parsing(raw_author_string)

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        raw_date_str: str = self.precomputed.doc.xpath(
            "normalize-space(" '//ul[@class="smallList"]' '/li[strong[contains(text(), "Datum")]]' "/text())"
        )
        return generic_date_parsing(raw_date_str)

    @attribute
    def title(self) -> Optional[str]:
        return generic_text_extraction_with_css(self.precomputed.doc, self._title_selector)

    @attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get("keywords"))
