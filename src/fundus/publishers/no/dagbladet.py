import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_date_parsing,
    generic_nodes_to_text,
    generic_topic_parsing,
)


class DagbladetParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("#main > article > div.article-top.expand > div > header > h3")
        _subheadline_selector = CSSSelector("#main > article > div.body-copy > h2")
        _paragraph_selector = CSSSelector("#main > article > div.body-copy > p")

        _author_selector = CSSSelector("section.meta div[itemtype='http://schema.org/Person'] address.name")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def authors(self) -> List[str]:
            return generic_nodes_to_text(self._author_selector(self.precomputed.doc), normalize=True)

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("article:tag"))
