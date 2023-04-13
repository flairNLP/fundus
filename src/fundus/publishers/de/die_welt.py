import datetime
import re
from typing import List, Optional, Pattern

from lxml.cssselect import CSSSelector

from src.fundus.parser import ArticleBody, BaseParser, attribute
from src.fundus.parser.utility import (
    apply_substitution_pattern_over_list,
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class DieWeltParser(BaseParser):
    _author_substitution_pattern: Pattern[str] = re.compile(r"WELT")
    _paragraph_selector = CSSSelector("body .c-article-text > p")
    _summary_selector = CSSSelector("div.c-summary__intro")
    _subheadline_selector = CSSSelector(".c-article-text > h3")

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
        return apply_substitution_pattern_over_list(
            generic_author_parsing(self.precomputed.ld.bf_search("author")), self._author_substitution_pattern
        )

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

    @attribute
    def title(self) -> Optional[str]:
        return self.precomputed.ld.bf_search("headline")

    @attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get("keywords"))
