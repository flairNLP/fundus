import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import (
    ArticleBody,
    BaseParser,
    Image,
    ParserProxy,
    attribute,
    function,
)
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
    transform_breaks_to_paragraphs,
)


class NikkanGeadaiParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            "//div[@class='article-wrap'] //p[@class='full-text'] /p[@class='br-wrap' and text()]"
        )

        _full_text_selector = CSSSelector("div.article-wrap p.full-text")

        _topic_selector = XPath("//main //div[contains(@class, 'm-keyword-list')] /ul /li //text()")

        @function(priority=0)
        def _transform_br_element(self):
            if nodes := self._full_text_selector(self.precomputed.doc):
                if len(nodes) != 1:
                    raise ValueError(f"Expected exactly one node")
                else:
                    transform_breaks_to_paragraphs(nodes[0], __class__="br-wrap")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def topics(self) -> List[str]:
            if topics := self._topic_selector(self.precomputed.doc):
                return generic_topic_parsing(topics)
            return []

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=CSSSelector("div.article-wrap"),
                # https://regex101.com/r/uY6o2z/1
                author_selector=re.compile(r"（Ｃ）(?P<credits>.*?)\s*$"),
            )
