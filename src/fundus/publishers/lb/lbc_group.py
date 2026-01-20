import datetime
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_date_parsing,
    image_extraction,
    transform_breaks_to_paragraphs,
)


class LBCGroupParser(ParserProxy):
    class V1(BaseParser):
        _boilerplate = r"^Reuters$|^AFP$"

        _content_container_selector = XPath("//div[@class='LongDesc']//div[br]")
        _paragraph_selector = XPath(
            f"//p[@class='br-wrap' and not(re:test(normalize-space(string(.)), '{_boilerplate}')) and text()]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )

        @attribute
        def body(self) -> Optional[ArticleBody]:
            if nodes := self._content_container_selector(self.precomputed.doc):
                transform_breaks_to_paragraphs(nodes[0], __class__="br-wrap")
                return extract_article_body_with_selector(
                    self.precomputed.doc,
                    paragraph_selector=self._paragraph_selector,
                )
            return None

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                image_selector=XPath("//div[@itemprop='image' or @class='DimgContainer']//img"),
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//h1"),
                lower_boundary_selector=XPath("//div[@class='article_details_end_of_scroll']"),
            )
