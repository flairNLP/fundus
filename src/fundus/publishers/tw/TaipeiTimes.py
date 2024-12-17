import datetime
import re
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    image_extraction,
)


class TaipeiTimesParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            r"//div[@class='archives']/p[not(re:test(text(), '(?i)^（by.*）\s*$'))]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _summary_selector = XPath("//div[@class='archives']/h2")
        _author_selector = XPath("//div[@class='archives']//div[@class='name']/text()")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            author_selection = self._author_selector(self.precomputed.doc)
            if not author_selection:
                return []
            else:
                selection = re.sub(
                    r"(?is)(^by|/.*|staff reporter|(,?\s*with\s*)?staff writer.*)", "", author_selection[0]
                )
            return generic_author_parsing(selection, split_on=[r"\s+and\s+"])

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//div[@class='archives']"),
                image_selector=XPath("//div[@class='imgboxa']//img"),
                caption_selector=XPath("./ancestor::div[@class='imgboxa']//h1"),
                author_selector=XPath("./ancestor::div[@class='imgboxa']//p"),
            )
