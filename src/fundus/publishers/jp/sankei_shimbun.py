import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_nodes_to_text,
    generic_topic_parsing,
    image_extraction,
)


class SankeiShimbunParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            "//div[contains(@class, 'article-body')] "
            "/p[contains(@class, 'article-text ') and (text() or not(child::a))]"
        )
        _subheadline_selector = CSSSelector("div.article-body > h2")

        _topic_selector = CSSSelector("ul.section-list > li")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def authors(self) -> List[str]:
            return [
                author for author in generic_author_parsing(self.precomputed.meta.get("author")) if "産経新聞" not in author
            ]

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def topics(self) -> List[str]:
            if topic_nodes := self._topic_selector(self.precomputed.doc):
                return generic_topic_parsing("・".join(generic_nodes_to_text(topic_nodes)), "・")
            return []

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                lower_boundary_selector=CSSSelector("div.article-footer-wrapper"),
                # https://regex101.com/r/gljUs9/1
                author_selector=re.compile(r"（.*?(?P<credits>[^（、]*?)撮影）"),
            )
