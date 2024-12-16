import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    image_extraction,
)


class FrankfurterRundschauParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            "//p[@class='id-StoryElement-paragraph'] | "
            "//p[contains(@class,'id-Article-content-item-paragraph') and text()] |"
            "//div[@class='id-Article-body']//ul/li[not(@class='id-AuthorList-item ')]"
        )
        _summary_selector = CSSSelector(
            "p.id-StoryElement-leadText, p[class='id-Article-content-item id-Article-content-item-summary']"
        )
        _subheadline_selector = CSSSelector("h2.id-StoryElement-crosshead, span.id-Article-content-item-headline-text")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=CSSSelector("article"),
                author_selector=re.compile(r"©(?P<credits>.+)"),
            )
