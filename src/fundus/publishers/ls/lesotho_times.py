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
            return generic_author_parsing(generic_nodes_to_text(self._author_selector(self.precomputed.doc)))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//div[@class='feature-postimg']/img"),
                upper_boundary_selector=XPath("//header"),
            )
