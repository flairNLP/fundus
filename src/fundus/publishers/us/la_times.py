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


class LATimesParser(ParserProxy):
    class V1(BaseParser):
        _subheadline_selector = CSSSelector(
            "div[data-element*=story-body] h3[class*=story-title], div[data-element*=story-body] h2[class=subhead]"
        )
        _paragraph_selector = CSSSelector("div[data-element*=story-body] > p")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//div[@class='page-lead']|//h1[@class='headline']"),
                caption_selector=XPath("./ancestor::figure//div[@class='figure-caption']"),
                author_selector=XPath("./ancestor::figure//div[@class='figure-credit']"),
            )
