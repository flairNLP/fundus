import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class WiredParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath("//div[contains(@class, 'ContentHeaderDek')]")
        _paragraph_selector = CSSSelector(".body__inner-container > p")
        _subheadline_selector = CSSSelector(".body__inner-container h2")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//figure//img|//div[contains(@class, 'ProductEmbedWrapper')]//img"),
                caption_selector=XPath(
                    "./ancestor::*[self::figure or (self::div and contains(@class, 'ProductEmbedWrapper'))]"
                    "//*[contains(@class, 'caption__text') or contains(@class, 'ProductEmbedHed-')]"
                ),
                author_selector=XPath(
                    "./ancestor::*[self::figure or (self::div and contains(@class, 'ProductEmbedWrapper'))]"
                    "//*[contains(@class, 'caption__credit') or contains(@class, 'CreditWrapper')]"
                ),
            )
