import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class TAParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("p.ContentHead_lead____SsS")
        _subheadline_selector = CSSSelector("article > h2")
        _paragraph_selector = CSSSelector(
            "article > p"
            ":not(.ContentHead_lead____SsS)"
            ":not(.Feedback_root__fr_Mi)"
            ":not(.ArticleContainer_agencies__g6Lpj)"
        )

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")
