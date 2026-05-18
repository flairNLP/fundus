import datetime
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


class TagesAnzeigerParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2026, 5, 4)

        _summary_selector: XPath = CSSSelector("p.ContentHead_lead____SsS")
        _subheadline_selector: XPath = CSSSelector("article > h2")
        _paragraph_selector: XPath = CSSSelector(
            "article > p"
            ":not(.ContentHead_lead____SsS)"
            ":not(.Feedback_root__fr_Mi)"
            ":not(.ArticleContainer_agencies__g6Lpj)"
        )

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                caption_selector=XPath("./ancestor::figure//figcaption/div[1]"),
                author_selector=XPath("./ancestor::figure//figcaption/div[2]"),
                lower_boundary_selector=CSSSelector("div.EndOfArticleSectionList_root__LJO7G"),
            )

    class V1_1(V1):
        _paragraph_selector = XPath("//article//p[contains(@class, 'articleParagraph')]")
        _summary_selector = XPath(
            "//article//p[contains(@class, 'lead')] | "
            "//article//div[contains(@class, 'SummaryList')]//*[self::strong or self::li]"
        )
        _subheadline_selector = XPath("//article//h2[contains(@class, 'crosshead')]")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                caption_selector=XPath("./ancestor::figure//figcaption/div[1]"),
                author_selector=XPath("./ancestor::figure//figcaption/div[2]"),
            )
