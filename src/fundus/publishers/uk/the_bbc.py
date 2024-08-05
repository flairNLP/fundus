import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    normalize_whitespace,
)


class TheBBCParser(ParserProxy):
    class V1(BaseParser):
        _subheadline_selector = CSSSelector("div[data-component='subheadline-block']")
        _summary_selector = XPath("//div[@data-component='text-block'][1] //p[b]")
        _paragraph_selector = XPath(
            "//div[@data-component='text-block'][1]//p[not(b) and text()] |"
            "//div[@data-component='text-block'][position()>1] //p[text()] |"
            "//div[@data-component='text-block'] //ul /li[text()]"
        )

        _topic_selector = CSSSelector(
            "div[data-component='topic-list'] > div > div > ul > li ," "div[data-component='tags'] a"
        )

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
            )

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
            topic_nodes = self._topic_selector(self.precomputed.doc)
            return [normalize_whitespace(node.text_content()) for node in topic_nodes]
