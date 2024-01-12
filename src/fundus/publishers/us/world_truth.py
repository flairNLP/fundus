import datetime
from typing import Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute, function
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_date_parsing,
    get_meta_content,
    strip_nodes_to_text,
)


class WorldTruthParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2023, 12, 16)
        _paragraph_selector = CSSSelector(".td-post-content > p")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

    class V2(BaseParser):
        _meta_node_selector = CSSSelector("meta[itemprop]")

        @function(priority=1)
        def overwrite_meta(self):
            meta = get_meta_content(self.precomputed.doc, {"itemprop": self._meta_node_selector})
            self.precomputed.meta = meta

        _paragraph_selector = CSSSelector(".td-post-content > p")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("headline ")
