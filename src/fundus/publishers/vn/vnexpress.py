import re
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
    strip_nodes_to_text,
)


class VnExpressIntlParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("p.description")
        _paragraph_selector = XPath("//article[@class='fck_detail ']//p[not(@style or @class='author_mail')]")

        _author_selector = XPath(
            "//article[@class='fck_detail ']//p[@style='text-align:right;' or @class='author_mail']"
        )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.xpath_search("//NewsArticle/headline", scalar=True)

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(strip_nodes_to_text(self._author_selector(self.precomputed.doc)))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.ld.xpath_search("//NewsArticle/datePublished", scalar=True))

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                author_selector=re.compile(r"(?i)Ảnh:\s*(?P<credits>.+)$"),
                upper_boundary_selector=XPath("//h1"),
            )

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"), result_filter={"Tin nóng"})
