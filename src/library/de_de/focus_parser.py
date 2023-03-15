import datetime
import re
from typing import List, Match, Optional, Pattern

from src.parser.html_parser import ArticleBody, BaseParser, register_attribute
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class FocusParser(BaseParser):
    _author_substitution_pattern: Pattern[str] = re.compile(r"Von FOCUS-online-(Redakteur|Autorin)\s")
    _topic_pattern: Pattern[str] = re.compile(r'"keywords":\[{(.*?)}\]')
    _topic_name_pattern: Pattern[str] = re.compile(r'"name":"(.*?)"', flags=re.MULTILINE)

    @register_attribute
    def body(self) -> Optional[ArticleBody]:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            summary_selector="div.leadIn > p",
            subheadline_selector="div.textBlock > h2",
            paragraph_selector="div.textBlock > p",
        )

    @register_attribute
    def authors(self) -> List[str]:
        author_names = generic_author_parsing(self.precomputed.ld.bf_search("author"))
        for i, name in enumerate(author_names):
            author_names[i] = re.sub(self._author_substitution_pattern, "", name)
        return author_names

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

    @register_attribute
    def title(self):
        return self.precomputed.ld.get("headline")

    @register_attribute
    def topics(self) -> List[str]:
        snippet = self.precomputed.doc.xpath(
            'string(//script[@type="text/javascript"][contains(text(), "window.bf__bfa_metadata")])'
        )
        if not snippet:
            return []

        match: Optional[Match[str]] = re.search(self._topic_pattern, snippet)
        if not match:
            return []
        topic_names: List[str] = re.findall(self._topic_name_pattern, match.group(1))

        return topic_names
