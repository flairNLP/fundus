import datetime
import re
from typing import List, Optional, Pattern

from src.parser.html_parser import ArticleBody, BaseParser, attribute
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    apply_substitution_pattern_over_list,
)


class DieZeitParser(BaseParser):
    _author_substitution_pattern: Pattern[str] = re.compile(r"DIE ZEIT (Archiv)")

    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            summary_selector="div.summary",
            subheadline_selector="div.article-page > h2",
            paragraph_selector="div.article-page > p",
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
    def title(self):
        return self.precomputed.ld.bf_search("headline")

    @attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get("keywords"))
