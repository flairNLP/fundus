import datetime
import re
from typing import List, Optional, Pattern

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    apply_substitution_pattern_over_list,
    extract_article_body_with_selector,
    generic_date_parsing,
    generic_text_extraction_with_css,
    generic_topic_parsing,
)


class MDRParser(ParserProxy):
    class V1(BaseParser):
        _author_substitution_pattern: Pattern[str] = re.compile(r"MDR \w*$|MDR \w*-\w*$|MDRfragt-Redaktionsteam|^von")
        _paragraph_selector = CSSSelector("div.paragraph")
        _summary_selector = CSSSelector("p.einleitung")
        _subheadline_selector = CSSSelector("div > .subtitle")
        _author_selector = CSSSelector(".articleMeta > .author")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("news_keywords"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            if raw_author_str := generic_text_extraction_with_css(self.precomputed.doc, self._author_selector):
                raw_author_str = raw_author_str.replace(" und ", ", ")
                author_list = [name.strip() for name in raw_author_str.split(",")]
                return apply_substitution_pattern_over_list(author_list, self._author_substitution_pattern)

            return []

        @attribute
        def title(self) -> Optional[str]:
            return title if isinstance(title := self.precomputed.ld.bf_search("headline"), str) else None
