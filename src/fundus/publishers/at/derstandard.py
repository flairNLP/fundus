from fundus.parser import ParserProxy, BaseParser
from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from typing import List, Optional
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)

from lxml.cssselect import CSSSelector
import datetime


class DerStandardParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("div.article-body > p")
        _summary_selector = CSSSelector("h1.article-title")
        _subheadline_selector = CSSSelector("p.article-subtitle")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
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
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))


