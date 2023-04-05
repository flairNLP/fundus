import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from src.parser.html_parser import ArticleBody, BaseParser, attribute
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)




class TagesschauParser(BaseParser):
    _paragraph_selector = XPath("//article/p[position() > 1]")
    _summary_selector =XPath("//article/p[1]")
    _subheadline_selector = XPath("//article/h2")

    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            summary_selector=self._summary_selector,
            subheadline_selector=self._subheadline_selector,
            paragraph_selector=self._paragraph_selector,
        )

    @attribute
    def authors(self) -> List[str]:
        if raw_author_string := self.precomputed.doc.xpath('string(//div[contains(@class, "authorline__author")])'):
            cleaned_author_string = re.sub(r"^Von |, ARD[^\s,]*", "", raw_author_string)
            return generic_author_parsing(cleaned_author_string)
        else:
            return []

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

    @attribute
    def title(self) -> Optional[str]:
        return self.precomputed.meta.get("og:title")

    @attribute
    def topics(self) -> List[str]:
        topic_nodes = self.precomputed.doc.cssselect("div.meldungsfooter .taglist a")
        return [node.text_content() for node in topic_nodes]
