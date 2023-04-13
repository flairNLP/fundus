import datetime
import re
from typing import List, Optional, Pattern

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from src.fundus.parser import ArticleBody, BaseParser, attribute
from src.fundus.parser.utility import (
    apply_substitution_pattern_over_list,
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class NTVParser(BaseParser):
    _author_substitution_pattern: Pattern[str] = re.compile(r"n-tv NACHRICHTEN")
    _summary_selector = XPath("//div[@class='article__text']/p[not(last()) and strong][1]")
    _paragraph_selector = XPath(
        "//div[@class='article__text']" "/p[not(strong) or (strong and (position() > 1 or last()))]"
    )
    _subheadline_selector = CSSSelector(".article__text > h2")

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
        initial_list = generic_author_parsing(self.precomputed.meta.get("author"))
        return apply_substitution_pattern_over_list(initial_list, self._author_substitution_pattern)

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.meta.get("date"))

    @attribute
    def title(self) -> Optional[str]:
        return self.precomputed.meta.get("og:title")

    @attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get("keywords"))
