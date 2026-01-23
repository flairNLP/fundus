import datetime
import re
from typing import List, Optional

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
    generic_nodes_to_text,
    generic_topic_parsing,
    image_extraction,
    transform_breaks_to_paragraphs,
)


class EyethuNewsParser(ParserProxy):
    class V1(BaseParser):
        _malformed_paragraph_selector = XPath("//div[contains(@class, 'entry-content')]/p[br]")

        _paragraph_selector = XPath("//div[contains(@class, 'entry-content')]/p[text() and not(a)] | //blockquote")
        _summary_selector = XPath("//h2[@class='entry-sub-title']")
        _subheadline_selector = XPath("//div[contains(@class, 'entry-content')]/p[not(text() or a)]/strong[not(a)]")

        _author_selector = XPath("//header//span[@class='meta-author']")

        @function(priority=1)
        def _break_malformed_paragraphs(self) -> None:
            for node in self._malformed_paragraph_selector(self.precomputed.doc):
                transform_breaks_to_paragraphs(node, replace=True)

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
            return generic_author_parsing(
                generic_nodes_to_text(self._author_selector(self.precomputed.doc)),
                result_filter=re.compile(r"(?i)content "),
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

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
                image_selector=XPath("//article//img[@alt]"),
                upper_boundary_selector=XPath("//h1"),
                author_selector=re.compile(r"(ISITHOMBE:|PHOTO:|IMAGE:)(?P<credits>.+)", flags=re.IGNORECASE),
            )
