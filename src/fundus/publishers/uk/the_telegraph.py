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


class TheTelegraphParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("div.articleBodyText p")
        _subheadline_selector = CSSSelector("div.articleBodyText h2")
        _summary_selector = CSSSelector("p[itemprop='description']")
        _datetime_selector = CSSSelector("time[itemprop='datePublished']")

        @attribute
        def body(self) -> ArticleBody:
            body = extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )
            return body

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            datetime_nodes = self._datetime_selector(self.precomputed.doc)
            if datetime_nodes:
                return generic_date_parsing(datetime_nodes[0].get("datetime"))
            return None

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("DCSext.author"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))
