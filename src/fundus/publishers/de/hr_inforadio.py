import datetime
import re
from typing import List, Optional, Pattern

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    apply_substitution_pattern_over_list,
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_text_extraction_with_css,
    generic_topic_parsing,
    strip_nodes_to_text,
)


class HRInforadioParser(ParserProxy):
    class V1(BaseParser):
         _summary_selector = CSSSelector("strong[data-cy='intro']")
        _paragraph_selector = CSSSelector("div[data-cy='article-content'] p")
        _subheadline_selector = CSSSelector("div[data-cy='article-content'] h2")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

    class V2_1(V2):
        VALID_UNTIL = datetime.date.today()

        _topic_selector = CSSSelector("header > div.kicker > span")

        @attribute
        def topics(self) -> List[str]:
            topic_nodes = self._topic_selector(self.precomputed.doc)
            if (topic_string := strip_nodes_to_text(topic_nodes, join_on=", ")) is not None:
                return topic_string.split(", ")
            return []

    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2023, 6, 12)

        _paragraph_selector = CSSSelector("div.longText > p")
        _summary_selector = CSSSelector("p.intro")
        _subheadline_selector = CSSSelector("div.longText > h2")
        _title_selector = CSSSelector(".col3 h1")
        _author_selector = XPath(
            "normalize-space(" '//ul[@class="smallList"]' '/li[strong[contains(text(), "Auto")]]' "/text()[last()]" ")"
        )
        _date_selector = XPath(
            "normalize-space(" '//ul[@class="smallList"]' '/li[strong[contains(text(), "Datum")]]' "/text())"
        )

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
            raw_author_string: str = self._author_selector(self.precomputed.doc)
            return generic_author_parsing(raw_author_string)

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            raw_date_str: str = self._date_selector(self.precomputed.doc)
            return generic_date_parsing(raw_date_str)

        @attribute
        def title(self) -> Optional[str]:
            return generic_text_extraction_with_css(self.precomputed.doc, self._title_selector)

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))
