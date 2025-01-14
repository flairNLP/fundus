import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_date_parsing,
    image_extraction,
)


class NikkeiParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("section[data-track-article-content] > p")
        _subheadline_selector = CSSSelector("section[data-track-article-content] > div > h2")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                lower_boundary_selector=CSSSelector("div.paywall_pzomzzc"),
            )
