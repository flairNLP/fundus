from datetime import datetime
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


class DerFreitagParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("header > p.bc-article-intro__text")
        _paragraph_selector = CSSSelector("div.bo-article-text > p")
        _subheadline_selector = CSSSelector("div.bo-article-text > h2")

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

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
        def topics(self) -> List[str]:
            return self.precomputed.ld.bf_search("keywords")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=CSSSelector("header.bc-article-intro"),
                lower_boundary_selector=CSSSelector("span.freitag-article-end"),
                image_selector=CSSSelector("figure img,div[role='figure'] img"),
                caption_selector=XPath("./ancestor::figure//figcaption//span[@class='bo-image__caption__desc']"),
                author_selector=XPath("./ancestor::figure//figcaption//span[@class='bo-image__caption__credit']"),
            )
