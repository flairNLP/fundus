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


class TheMirrorParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("/html/body/main/article/div[2]/p[text()]")
        _summary_selector = XPath("/html/body/main/article/div[1]/p")
        _datetime_selector = XPath("//li/span[contains(@class, 'time-container')]")

        @attribute
        def body(self) -> ArticleBody:
            body = extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
            )
            return body

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("parsely-pub-date"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("author"))

        @attribute
        def topics(self) -> List[str]:
            news_keywords = self.precomputed.meta.get("news_keywords", "").split(",")
            return [news_keywords.strip() for news_keywords in news_keywords if news_keywords.strip()]
