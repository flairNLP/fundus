import datetime
import re
from typing import List, Optional, Pattern

from src.parser.html_parser import ArticleBody, BaseParser, attribute
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_text_extraction_with_css,
    generic_topic_parsing,
)


class NtvParser(BaseParser):
    _author_substitution_pattern: Pattern[str] = re.compile(r"n-tv NACHRICHTEN")

    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            paragraph_selector=".article__text > p",
            subheadline_selector=".article__text > h2",
        )

    @attribute
    def authors(self) -> List[str]:
        initial_list = generic_author_parsing(self.precomputed.meta.get("author"))
        cleaned_list = [re.sub(self._author_substitution_pattern, "", el) for el in initial_list]
        return [el for el in cleaned_list if el]

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.meta.get("date"))

    @attribute
    def title(self):
        return self.precomputed.meta.get("og:title")

    @attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get("keywords"))
