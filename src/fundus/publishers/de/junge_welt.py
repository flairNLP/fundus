import datetime
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


class JungeWeltParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            "//div[@class = 'row']/div[contains(@class, 'col') and not(@class = 'col-md-8 mx-auto mt-4 bg-light')]/p"
        )
        _summary_selector = CSSSelector(".teaser.lead")
        _subheadline_selector = XPath("//div[@class = 'row']/div[contains(@class,'col')]/h3")
        _free_access_selector = XPath("//h1[text()='Sie sind nun eingeloggt.']|//p[@class='m-1']")

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
            return generic_author_parsing(self.precomputed.meta.get("Author"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def free_access(self) -> bool:
            return not bool(self._free_access_selector(self.precomputed.doc))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))
