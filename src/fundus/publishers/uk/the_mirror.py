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

class TheMirrorParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("div.lead-content__title h1")
        _summary_selector = CSSSelector("p[itemprop='description']")
        _datetime_selector = CSSSelector("time.date-published")
        
        
        @attribute
        def body(self) -> ArticleBody:
            body = extract_article_body_with_selector(
                self.precomputed.doc, 
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector)
            return body

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))
        
        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")
