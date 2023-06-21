import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class OccupyDemocratsParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector: CSSSelector = CSSSelector(
            "div[itemprop='articleBody']>p, div[itemprop='articleBody']>blockquote"
        )

        @attribute
        def body(self) -> ArticleBody:
            body: ArticleBody = extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
            )
            return body

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("Person"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def title(self) -> Optional[str]:
            title: Optional[str] = self.precomputed.meta.get("og:title")
            return title

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.get_value_by_key_path(["Article", "keywords"]))

        @attribute(validate=False)
        def description(self) -> Optional[str]:
            return self.precomputed.meta.get("description")
