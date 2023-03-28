import datetime
import re
from typing import List, Optional, Pattern

from src.parser.html_parser import ArticleBody, BaseParser, attribute
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing, substitute_all_strs_in_list,
)


class DieWeltParser(BaseParser):
    _author_substitution_pattern: Pattern[str] = re.compile(
        r"WELT"
    )
    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            summary_selector="div.c-summary__intro",
            subheadline_selector=".c-article-text > h3",
            paragraph_selector="body .c-article-text > p",
        )

    @attribute
    def authors(self) -> List[str]:
        return substitute_all_strs_in_list(generic_author_parsing(self.precomputed.ld.bf_search("author")), self._author_substitution_pattern)


    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

    @attribute
    def title(self):
        return self.precomputed.ld.bf_search("headline")

    @attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get("keywords"))
