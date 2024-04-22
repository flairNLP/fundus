import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class ZDFParser(ParserProxy):
    class V1(BaseParser):
        _div_selector = CSSSelector("div.r1nj4qn5")
        _summary_selector = CSSSelector("p.ikh9v7p.c1bdz7f4")
        _subheadlines_selector = CSSSelector("h2.t1rbo974.hhhtovw")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._div_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadlines_selector,
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
