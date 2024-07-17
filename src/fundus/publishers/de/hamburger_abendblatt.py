import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class HamburgerAbendblattParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("div.article-body > p.font-sans")
        _paragraph_selector = CSSSelector("div.article-body > p:not(.font-sans)")
        _subheadline_selector = CSSSelector("div.article-body > h3")
        _topics_selector = XPath("//div[@class='not-prose  mb-4 mx-5 font-sans']/ul/li")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            if topics := generic_topic_parsing(self.precomputed.meta.get("keywords")):
                return topics
            else:
                return [
                    re.sub(r"\s*–.+", "", node.text_content()).strip()
                    for node in self._topics_selector(self.precomputed.doc)
                ]
