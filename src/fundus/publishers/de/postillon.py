import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_date_parsing,
    image_extraction,
)


class PostillonParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("div[id=post-body] p")
        _postscript_selector = CSSSelector("div[id=post-body] > span")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def authors(self) -> List[str]:
            postscript = self._postscript_selector(self.precomputed.doc)
            if not postscript:
                return []
            author_line = postscript[0].text_content().split(";")[0]
            return [a.strip() for a in author_line.split(",")]

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//div[@class='entry-content-wrap flex-col']//img"),
            )
