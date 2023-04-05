import datetime
from typing import List, Optional

from src.parsing import ArticleBody, BaseParser, attribute
from src.parsing.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_text_extraction_with_css,
    generic_topic_parsing,
)


class DWParser(BaseParser):
    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            summary_selector="p.intro",
            subheadline_selector="div.longText > p",
            paragraph_selector="div.longText > h2",
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
        return generic_text_extraction_with_css(self.precomputed.doc, ".col3 h1")

    @attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get("keywords"))
