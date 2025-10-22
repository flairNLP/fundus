import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from fundus.parser import BaseParser, ParserProxy
from fundus.parser.base_parser import attribute
from fundus.parser.data import ArticleBody
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class MediaIndonesiaParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("div.article")
        _subheadline_selector = CSSSelector("div.article > h2")

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))
