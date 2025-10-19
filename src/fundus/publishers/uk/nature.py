import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    parse_title_from_root,
)


class NatureParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            "//div[contains(@class,'c-article-body')]//p | //div[contains(@class,'c-article-section__content')]//p"
        )
        _subheadline_selector = XPath("//h2[contains(@class,'c-article-section__heading')]")
        _author_selector = XPath("//li[contains(@class,'c-article-author')]//a")

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("dc.title") or parse_title_from_root(self.precomputed.doc)

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(
                [node.text_content() for node in self._author_selector(self.precomputed.doc) or []]
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(
                self.precomputed.meta.get("article:published_time") or self.precomputed.meta.get("dc.date")
            )
