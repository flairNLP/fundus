import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class EveningStandardParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2024, 6, 30)
        _paragraph_selector = CSSSelector("div.sc-bkSUFG.bdkDcZ")
        _summary_selector = CSSSelector("div.sc-wkolL.dWZJhQ")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()
        _summary_selector = CSSSelector("div.sc-jgyXzG")
        _subheadline_selector = CSSSelector("div#main div.sc-dFfFtc > h3")
        _paragraph_selector = CSSSelector("div#main > div.sc-gEvEer p")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )
