import datetime
import re
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.data import Image
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    image_extraction,
)


class JyllandsPostenParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            "//section/article/div[contains(@class, 'c-article-inline')]"
            "/div[contains(@class, 'c-article-inline')]"
            "/div[contains(@class, 'c-article-inline')]"
            "/div/div/p | "
            "//article/p[contains(@class, '-text') and text()]"
        )
        _summary_selector = XPath("//header/p")
        _subheadline_selector = XPath(
            "//section/article/div[contains(@class, 'c-article-inline')]"
            "/div[contains(@class, 'c-article-inline')]"
            "/div[contains(@class, 'c-article-inline')]"
            "/div/div/h3 | "
            "//article/h3"
        )

        _headline_selector = XPath("//h1/text()")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            headlines: List[str] = self._headline_selector(self.precomputed.doc)
            if headlines:
                return headlines[0].strip()
            return None

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(
                self.precomputed.ld.bf_search("author") or self.precomputed.meta.get("author"), split_on=["/"]
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                author_selector=re.compile(r"\s*(Foto|Arkivfoto):\s*(?P<credits>.*)\.?"),
            )
