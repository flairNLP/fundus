import re
from datetime import date, datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    image_extraction,
)


class GamestarParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = date(2026, 11, 24)
        _summary_selector = CSSSelector("p.intro")
        _paragraph_selector = CSSSelector("div.article-content > p:not([class])")
        _subheadline_selector = CSSSelector("div.article-content > h2")

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//div[@class='main waypoint']"),
                image_selector=XPath("//picture/img"),
                caption_selector=XPath("./ancestor::p[@class='caption ']/span[@class='bu m-t-1']"),
                lower_boundary_selector=XPath("//div[@id='comments']"),
                author_selector=re.compile("(?i)Bildquelle:(?P<credits>.*)"),
                relative_urls=True,
            )

    class V1_1(V1):
        _paragraph_selector = CSSSelector(
            "div.article-content > p:not([class]), "
            "div.article-content > div.block-quote > p, "
            "div.article-content > cite > p, "
            "div.article-content > div.spoiler > div.spoiler-content > p, "
            "div.article-content > ul, "
            "div.article-content > ol"
        )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=CSSSelector("div.main.waypoint"),
                image_selector=XPath("//picture/img[not(@class='author-image')]"),
                caption_selector=XPath("./ancestor::p[@class='caption ']/span[@class='bu m-t-1']"),
                lower_boundary_selector=XPath("//div[@id='comments']"),
                author_selector=re.compile(r"(?i)\(?Bildquelle:\s*(?P<credits>[^)]*)\)?"),
                relative_urls=True,
            )
