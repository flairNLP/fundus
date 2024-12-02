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


class LeMondeParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector: CSSSelector = CSSSelector("p[class='article__paragraph ']")
        _summary_selector: XPath = XPath("//p[contains(@class, 'article__desc') or @id='js-summary-live']")
        _subheadline_selector: XPath = XPath("//h2[@class = 'article__sub-title']")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            # Use the `get` function to retrieve data from the `meta` precomputed attribute
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return self.precomputed.ld.bf_search("keywords")  # type: ignore

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            # Use the `get` function to retrieve data from the `meta` precomputed attribute
            return generic_date_parsing(self.precomputed.meta.get("og:article:published_time"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("og:article:author"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=CSSSelector("article"),
                image_selector=XPath("//figure/descendant::img[1]"),
                caption_selector=XPath("./ancestor::figure//figcaption/text()"),
                author_selector=XPath("./ancestor::figure//figcaption/span"),
            )
