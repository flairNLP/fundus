import datetime
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_nodes_to_text,
    image_extraction,
)


class LesothoTimesParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2025, 9, 20)

        _paragraph_selector = XPath("//div[@class='entry-content']/p[text() or span]")
        _subheadline_selector = XPath(
            "//div[@class='entry-content']/p[not(text() or em) and strong[not(em)] and position()>4]"
        )
        _summary_selector = XPath("//div[@class='entry-content']/p[not(text()) and (strong[em] or em)]")

        _author_selector = XPath(
            "//div[@class='entry-content']/p[not(text() or em) and strong[not(em)] and position()<5]"
        )

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(
                generic_nodes_to_text(self._author_selector(self.precomputed.doc)), split_on=["/"]
            )

        @attribute
        def title(self) -> Optional[str]:
            if title := self.precomputed.meta.get("og:title"):
                return title.replace("- Lesotho Times", "").strip()
            return None

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//div[@class='feature-postimg']/img"),
                upper_boundary_selector=XPath("//header"),
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()

        _paragraph_selector = XPath(
            "//div[contains(@class,'entry-content')]/p["
            "(text() or span) and "
            "not(i or "
            "(string-length(normalize-space(.)) - string-length(translate(normalize-space(.), ' ', ''))+ 1 <=3"
            " and position()<5"
            "))]"
        )
        _subheadline_selector = XPath(
            "//div[contains(@class,'entry-content')]/p[i or (not(text() or em) and strong[not(em)] and position()>4)]"
        )
        _summary_selector = XPath("//div[contains(@class,'entry-content')]/p[not(text()) and (strong[em] or em)]")

        _author_selector = XPath(
            "//div[contains(@class,'entry-content')]/p["
            "string-length(normalize-space(.)) - string-length(translate(normalize-space(.), ' ', '')) + 1 <=3"
            " and position()<5"
            "]"
        )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//div[@class='feature-postimg' or contains(@class, 'post-image')]/img"),
                caption_selector=XPath("./ancestor::div[contains(@class,'media')]//figcaption"),
                upper_boundary_selector=XPath("//header"),
            )
