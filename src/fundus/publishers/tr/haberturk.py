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


class HaberturkParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath("//article//h2[preceding-sibling::h1]")
        _paragraph_selector = CSSSelector("article p")
        _subheadline_Selector = XPath("//article//h2[not(preceding-sibling::h1)]")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_Selector,
            )

        @attribute(validate=False)
        def description(self) -> Optional[str]:
            return self.precomputed.meta.get("og:description")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(
                self.precomputed.ld.bf_search("datePublished") or self.precomputed.meta.get("datePublished")
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=CSSSelector("article"),
                image_selector=CSSSelector("img[data-zoomable]"),
            )
