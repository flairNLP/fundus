from datetime import datetime
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


class SPONParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("main .word-wrap > p")
        _summary_selector = CSSSelector("header .leading-loose")
        _subheadline_selector = CSSSelector("main .word-wrap > h3")

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
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("news_keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                lower_boundary_selector=XPath("//footer"),
                image_selector=XPath("//figure//picture//img"),
                caption_selector=XPath(
                    "./ancestor::figure/following-sibling::figcaption[1]//p|" "./ancestor::figure/figcaption[1]//p"
                ),
                author_selector=XPath(
                    "./ancestor::figure/following-sibling::figcaption[1]/span|"
                    "./ancestor::figure/figcaption[1]/*[(self::span or self::div) and contains(@class,'Credit')]"
                ),
            )
