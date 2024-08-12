import datetime
import json
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath
from lxml.html import document_fromstring

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class CBCNewsParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("h2.deck")
        _subheadline_selector = CSSSelector("div.story > h2")
        _paragraph_selector = CSSSelector("div.story > p")

        _author_ld_selector = XPath("//script[@id='initialStateDom']")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            doc = document_fromstring(self.precomputed.html)
            ld_nodes = self._author_ld_selector(doc)
            try:
                author_ld = json.loads(re.sub(r"(window\.__INITIAL_STATE__ = |;$)", "", ld_nodes[0].text_content()))
            except json.JSONDecodeError:
                return []
            if not (details := author_ld.get("detail")):
                return []
            if not (content := details.get("content")):
                return []
            return generic_author_parsing(content.get("authorList"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("ReportageNewsArticle")[0].get("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            if not (title := self.precomputed.meta.get("og:title")):
                return title
            return re.sub(r" \|.*", "", title)

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.bf_search("ReportageNewsArticle")[0].get("articleSection"))
