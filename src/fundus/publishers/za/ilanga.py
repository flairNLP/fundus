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
        _paragraph_selector = XPath(
            "(//div[contains(@class,'post_content')]//p["
            "string() and "  # sometimes strong paragraphs are used for emphasis, hence filter by position
            "not(position()<4 and strong and not(text())) and "  # Exclude author option 1
            "not(position()<4 and string-length(text()) - string-length(translate(text(), ' ', '')) < 3) and"  # Exclude author option 2
            "not(re:test(text(), '^\s*[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z.]{2,}\s*$'))"  # Exclude emails
            "])[not(strong and not(text()) and preceding-sibling::*[position()=1 and self::figure])]",  # Exclude image captions
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )

        _author_selector = XPath(
            "(//div[contains(@class,'post_content')]//p["
            "string() and position()<4])[(strong and not(text())) or "
            "string-length(text()) - string-length(translate(text(), ' ', '')) < 3"
            "]"
        )

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
                lower_boundary_selector=XPath("//div[@class='dtb-related-posts']"),
                caption_selector=XPath(
                    "(./ancestor::figure/following-sibling::p[position()=1])[strong and not(text())]"
                ),
            )
