import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from src.parser.html_parser import ArticleBody, BaseParser, attribute
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class SternParser(BaseParser):
    _paragraph_selector = CSSSelector(".article__body >p")
    _summary_selector = CSSSelector(".intro__text")
    _subheadline_selector = CSSSelector(".subheadline-element")

    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            summary_selector=self._summary_selector,
            subheadline_selector=self._subheadline_selector,
            paragraph_selector=self._paragraph_selector,
        )

    @attribute
    def authors(self) -> List[str]:
        initial_authors = generic_author_parsing(self.precomputed.ld.bf_search("author"))
        return [el for el in initial_authors if el != "STERN.de"]

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(
            self.precomputed.meta.get(
                "date",
            )
        )

    @attribute
    def title(self) -> Optional[str]:
        return self.precomputed.meta.get("og:title")

    @attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get("sis-article-keywords"), delimiter="|")