import datetime
import re
from typing import List, Optional, Pattern

from src.parser.html_parser import ArticleBody, BaseParser, attribute
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_date_parsing,
    generic_text_extraction_with_css,
    generic_topic_parsing,
    substitute_all_strs_in_list,
)


class MDRParser(BaseParser):
    _author_substitution_pattern: Pattern[str] = re.compile(r"MDR \w*$|MDR \w*-\w*$|MDRfragt-Redaktionsteam|von")

    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            summary_selector="p.einleitung",
            subheadline_selector="div > .subtitle",
            paragraph_selector="div.paragraph",
        )

    @attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get("news_keywords"))

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

    @attribute
    def authors(self) -> List[str]:
        if raw_author_str := generic_text_extraction_with_css(self.precomputed.doc, ".articleMeta > .author"):
            raw_author_str = raw_author_str.replace(" und ", ", ")
            author_list = [name.strip() for name in raw_author_str.split(",")]
            return substitute_all_strs_in_list(author_list, self._author_substitution_pattern)

        return []

    @attribute
    def title(self) -> Optional[str]:
        return title if isinstance(title := self.precomputed.ld.bf_search("headline"), str) else None
