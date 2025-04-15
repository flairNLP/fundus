import datetime
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    image_extraction,
)


class NineNewsParser(ParserProxy):
    class V1(BaseParser):
        # _paragraph_selector = CSSSelector("div.article__body div.block-content")

        _bloat_regex = r"^READ MORE:"
        _paragraph_selector = XPath(
            f"//div[@class='article__body'] "
            f"//div[@class='block-content'] "
            f"/div[child::span and not(re:test(string(), '{_bloat_regex}'))]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _subheadline_selector = XPath("//div[@class='article__body'] //div[@class='block-content'] /div[child::h3]")

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
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                caption_selector=XPath("./ancestor::figure//figcaption/text()[1]"),
                author_selector=XPath("./ancestor::figure//figcaption/text()[last()]"),
            )
