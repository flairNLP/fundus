import datetime
import re
from typing import List, Optional

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


class IlangaParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[contains(@class,'post_content')]//p[text() and not(strong)]")

        _author_selector = XPath("(//div[contains(@class,'post_content')]//p[position()=1])[strong and not(text())]")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            if authors := generic_author_parsing(strip_nodes_to_text(self._author_selector(self.precomputed.doc))):
                return authors
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return re.sub(re.compile(r"(?i)\s*-\s*ilanga news"), "", self.precomputed.ld.bf_search("headline"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//div[contains(@class,'post_content')]"),
                caption_selector=XPath(
                    "(./ancestor::figure/following-sibling::p[position()=1])[strong and not(text())]"
                ),
            )
