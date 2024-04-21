import datetime
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class BRParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath(
            "//p[starts-with(@class, 'ArticleModuleTeaser_teaserText') or starts-with(@class, 'ArticleItemTeaserText_text')]"
        )
        # paragraph_selector captures div contents for full article, p for teaser-only flash articles
        _paragraph_selector = XPath(
            "(//div[starts-with(@class, 'ArticleModuleText_content')]//p) | //p[starts-with(@class, 'ArticleItemTeaserText_text')]"
        )

        @attribute
        def title(self) -> Optional[str]:
            return title if isinstance(title := self.precomputed.ld.bf_search("headline"), str) else None

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))
