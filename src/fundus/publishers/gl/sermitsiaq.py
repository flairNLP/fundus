import datetime
import re
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


class SermitsiaqParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            f"//div[contains(@class, 'bodytext')]//p[not(@class='offer-description' or re:test(text(), '^/.*/$'))]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _summary_selector = XPath("//h2[@class='subtitle '] ")
        _subheadline_selector = XPath("//div[contains(@class, 'bodytext')]//h3[not(@class='offer-name')]")

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
            return generic_author_parsing(self.precomputed.ld.bf_search("author"), split_on=["og"])

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return [tag.title() for tag in generic_topic_parsing(self.precomputed.meta.get("article:tag"))]

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//figure//img[not(@itemprop='image')]"),
                caption_selector=XPath(
                    "./ancestor::*[self::figure or (self::div and contains(@class,'articleHeader'))]"
                    "//figcaption[@itemprop='caption']"
                ),
                author_selector=XPath(
                    "./ancestor::*[self::figure or (self::div and contains(@class,'articleHeader'))]"
                    "//figcaption[@itemprop='author']"
                ),
            )
