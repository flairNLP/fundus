import datetime
from typing import List, Optional

import lxml
from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class LeFigaroParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector: CSSSelector = CSSSelector("p[class='fig-paragraph']")
        _subheadline_selector: CSSSelector = CSSSelector("div > h2")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def description(self) -> Optional[str]:
            return self.precomputed.meta.get("og:description")

        @attribute
        def subheadlines(self) -> Optional[List[str]]:
            root = lxml.html.document_fromstring(self.precomputed.html)
            nodes = self._subheadline_selector(root)
            subheadlines = [node.text_content().replace('\xa0', ' ').strip() for node in nodes if
                            node.text_content().strip()]

            return subheadlines


