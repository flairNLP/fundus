from datetime import date, datetime
from typing import List, Optional, Union

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import (
    ArticleBody,
    BaseParser,
    ParserProxy,
    Selector,
    attribute,
    function,
)
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class TheNationParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = date(2023, 7, 22)

        # There is a known issue preventing lxml from extracting text content within
        # the specified summary node.
        # This is due to invalid XML provided by The Nation.
        # Currently(lxml 4.9.3), lxml does not accept p tags within any heading (h*) tag.
        # The "correct" selector would be ".article-header-content > h2 > p"
        _summary_selector: Selector = CSSSelector(".article-header-content > h2")
        _paragraph_selector = CSSSelector(".article-body-inner > p")
        _aside_selector = CSSSelector("aside")

        # We remove aside tags here because the provided HTML does not enclose <p> tags
        # within .article-header-content. As a result, <aside> tags following <p> tags get attached
        # to the paragraph. This is valid HTML5 behaviour.
        # see https://stackoverflow.com/questions/8460993/p-end-tag-p-is-not-needed-in-html
        @function(priority=1)
        def _remove_aside(self) -> None:
            for aside in self._aside_selector(self.precomputed.doc):
                if (parent := aside.getparent()) is not None:
                    parent.remove(aside)

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("sailthru.author"))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

    class V2(V1):
        VALID_UNTIL = date.today()

        _summary_selector = XPath("//article//div[contains(@class, 'article-title')]//p")
        _paragraph_selector = CSSSelector("article > p")

        # remove aside function from V1
        def _remove_aside(self):
            pass
