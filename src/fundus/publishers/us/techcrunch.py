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


class TechCrunchParser(ParserProxy):
    class V2(BaseParser):
        _summary_selector: XPath = CSSSelector("div.entry-content > p#speakable-summary")
        _paragraph_selector: XPath = CSSSelector("div.entry-content > p:not(#speakable-summary)")
        _subheadline_selector: CSSSelector = CSSSelector("div.entry-content > h2")

        @attribute
        def body(self) -> ArticleBody:
            body: ArticleBody = extract_article_body_with_selector(
                self.precomputed.doc,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
            )
            return body

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))

    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2024, 5, 8)
        _summary_selector: XPath = CSSSelector("div.article-content > p#speakable-summary")
        _paragraph_selector: XPath = CSSSelector("div.article-content > p:not(#speakable-summary)")
        _subheadline_selector: CSSSelector = CSSSelector("div.article-content > h2")

        @attribute
        def body(self) -> ArticleBody:
            body: ArticleBody = extract_article_body_with_selector(
                self.precomputed.doc,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
            )
            return body

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("sailthru.author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            if topics := generic_topic_parsing(self.precomputed.meta.get("keywords")):
                return topics
            else:
                return generic_topic_parsing(self.precomputed.meta.get("sailthru.tags"))
