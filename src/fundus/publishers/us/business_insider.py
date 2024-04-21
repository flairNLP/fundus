import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class BusinessInsiderParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("article ul[class^='summary-list'] > li")
        _subheadline_selector = CSSSelector("article h2, div.slideshow-slide-container h2")
        _paragraph_selector = XPath(
            """
            //article 
            //div[contains(@class, 'content-lock-content')] 
            /p[not(contains(@class, 'disclaimer'))] | 
            //article 
            //div[contains(@class, 'content-lock-content')]
            /div[contains(@class, 'premium-content')] 
            /p[not(contains(@class, 'disclaimer'))] | 
            //div[@class='slide-layout clearfix']
            /p[not(contains(@class, 'disclaimer'))]
            """
        )

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
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(
                self.precomputed.meta.get("keywords")
                or self.precomputed.ld.bf_search("keywords")
                or self.precomputed.meta.get("news_keywords")
            )
