import datetime
import re
from typing import List, Match, Optional, Pattern

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class FocusParser(BaseParser):
    # selectors
    _paragraph_selector = CSSSelector("div.textBlock > p")
    _summary_selector = CSSSelector("div.leadIn > p")
    _subheadline_selector = CSSSelector("div.textBlock > h2")
    _snippet_selector = XPath('string(//script[@type="text/javascript"][contains(text(), "window.bf__bfa_metadata")])')

    # regex patterns
    _author_substitution_pattern: Pattern[str] = re.compile(
        r"Von FOCUS-online-(Redakteur|Autorin|Reporter|Redakteurin|Gastautor)\s"
    )
    _topic_pattern: Pattern[str] = re.compile(r'"keywords":\[{(.*?)}\]')
    _topic_name_pattern: Pattern[str] = re.compile(r'"name":"(.*?)"', flags=re.MULTILINE)

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
        author_names = generic_author_parsing(self.precomputed.ld.bf_search("author"))
        for i, name in enumerate(author_names):
            author_names[i] = re.sub(self._author_substitution_pattern, "", name)
        return author_names

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

    @attribute
    def title(self) -> Optional[str]:
        return self.precomputed.ld.bf_search("headline")

    @attribute
    def topics(self) -> List[str]:
        snippet = self._snippet_selector(self.precomputed.doc)
        if not snippet:
            return []

        match: Optional[Match[str]] = re.search(self._topic_pattern, snippet)
        if not match:
            return []
        topic_names: List[str] = re.findall(self._topic_name_pattern, match.group(1))

        return topic_names
