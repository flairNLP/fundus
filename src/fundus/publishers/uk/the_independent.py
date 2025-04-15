import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class TheIndependentParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("article div[id='main'] > p")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            body = extract_article_body_with_selector(self.precomputed.doc, paragraph_selector=self._paragraph_selector)
            return body

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=CSSSelector("figure > div > img, div[data-gallery-length] > img"),
                upper_boundary_selector=CSSSelector("article"),
                author_selector=re.compile(r"(?P<credits>(\([^)]*\)\s?)+$)"),
            )
