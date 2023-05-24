import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class SternParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector(".article__body >p")
        _summary_selector = CSSSelector(".intro__text")
        _subheadline_selector = CSSSelector(".subheadline-element")

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
            topic_nodes = self.precomputed.doc.cssselect(".article__tags li.links__item")
            return [node.text_content().strip("\n ") for node in topic_nodes]
