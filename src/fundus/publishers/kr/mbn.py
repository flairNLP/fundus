from fundus.parser import ParserProxy, BaseParser, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)
from fundus.parser import ArticleBody
from lxml.cssselect import CSSSelector
from lxml.etree import XPath
from typing import Optional, List
from datetime import datetime

class MBNParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath(
            "//p[@class='post__excerpt'] | //h2[preceding-sibling::h1[contains(@class, 'post__title')]]"
        )

        _paragraph_selector = CSSSelector("[itemprop='articleBody'] > p")

        _subheadline_selector = CSSSelector(
            "div.entry-content > div.entry-content__content > h2"
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
            return generic_author_parsing(
                self.precomputed.ld.get_value_by_key_path(["NewsArticle", "author"])
            )

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(
                self.precomputed.ld.get_value_by_key_path(["NewsArticle", "datePublished"])
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.get_value_by_key_path(["NewsArticle", "headline"])

        @attribute
        def topics(self) -> List[str]:
            keywords: Optional[List[str]] = self.precomputed.ld.get_value_by_key_path(
                ["NewsArticle", "keywords"]
            )
            if not keywords:
                return []
            return [k[9:] for k in keywords if isinstance(k, str) and k.startswith("Subject: ")]

