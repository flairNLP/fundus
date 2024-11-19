import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    image_extraction,
)


class KickerParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("div[class=kick__article__content__child] > p")
        _summary_selector = CSSSelector("p[class=kick__article__teaser]")
        _subheadline_selector = CSSSelector("div[class=kick__article__content__child] > h2")

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
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//article"),
                image_selector=XPath(
                    "//*[contains(@class,'kick__article__picture') and not(contains(@class, 'medias'))]//img"
                ),
                caption_selector=XPath("./ancestor::*[contains(@class, 'kick__article__picture ')]//p/text()"),
                author_selector=XPath("./ancestor::*[contains(@class, 'kick__article__picture ')]//p/span"),
            )
