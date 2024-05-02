import datetime
from typing import Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class TagesspiegelParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("div[id=story-elements] > p")
        _subheadline_selector = CSSSelector(".Ha6")

        @attribute
        def body(self) -> ArticleBody:
            article_body = extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )
            return article_body

        @attribute
        def title(self) -> Optional[str]:
            # Use the `get` function to retrieve data from the `meta` precomputed attribute
            return self.precomputed.meta.get("og:title")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))
        
        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))
