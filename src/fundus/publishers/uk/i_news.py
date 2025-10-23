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


class INewsParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2025, 1, 1)
        _summary_selector = CSSSelector("article > h2")
        _paragraph_selector = CSSSelector("article div.article-content p")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            body = extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
            )
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
            return generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=CSSSelector("div.inews__main"),
                image_selector=CSSSelector("figure:has(> figcaption) img"),
                author_selector=re.compile(r"\((?P<credits>.*?)\)$"),
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()

        _summary_selector = CSSSelector("article p.inews__post-excerpt")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=CSSSelector("div.article-wrapper"),
                image_selector=CSSSelector("figure:has(> figcaption) img"),
                author_selector=re.compile(r"\((?P<credits>.*?)\)$"),
            )
