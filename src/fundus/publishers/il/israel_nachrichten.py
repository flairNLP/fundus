import datetime
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class IsraelNachrichtenParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[@id='main']/div[@class]/p[text()]")
        _summary_selector = XPath("//div[@id='main']/div[@class]/p/strong")
        _title_selector = XPath("//div[@id='main']/div[@class]/h1")

        _author_selector = XPath("//div[@id='main']/div[@class]/p/em")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            if authors := self._author_selector(self.precomputed.doc):
                return generic_author_parsing(authors[0].text_content())
            return []

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def title(self) -> Optional[str]:
            return (
                self._title_selector(self.precomputed.doc)[0].text_content().strip()
                if self._title_selector(self.precomputed.doc)
                else None
            )
