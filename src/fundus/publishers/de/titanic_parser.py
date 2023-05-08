import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_text_extraction_with_css,
    generic_topic_parsing,
)


class TitanicParser(BaseParser):
    _title_selector = CSSSelector(".csc-firstHeader")
    _paragraph_selector = XPath("//div[@class = 'bodytext']/p[position() > 1]")
    _summary_selector = XPath("//bodytext/p[1]")

    _paragraph_selector = CSSSelector(".bodytext")
    #This one is an open problem: The summary is the first paragraph. It is possible to extract this with xpath, I just dont get how.
    #The second version works, but includes the summary as a paragraph.

    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            summary_selector=self._summary_selector,
            paragraph_selector=self._paragraph_selector,
        )

    @attribute
    def authors(self) -> List[str]:
        return generic_author_parsing(self.precomputed.meta.get("author"))

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

    @attribute
    def title(self):
        return generic_text_extraction_with_css(self.precomputed.doc, self._title_selector)

    @attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))
