import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from src.fundus.parser import ArticleBody, BaseParser, attribute
from src.fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_date_parsing,
    generic_topic_parsing,
)


class FAZParser(BaseParser):
    _paragraph_selector = CSSSelector("div.atc-Text > p")
    _summary_selector = CSSSelector("div.atc-Intro > p")
    _subheadline_selector = CSSSelector("div.atc-Text > h3")
    _author_selector = CSSSelector(".atc-MetaAuthor")

    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            summary_selector=self._summary_selector,
            subheadline_selector=self._subheadline_selector,
            paragraph_selector=self._paragraph_selector,
        )

    @attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get("keywords"))

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

    @attribute
    def authors(self) -> List[str]:
        # Unfortunately, the raw data may contain cities. Most of these methods aims to remove the cities heuristically.
        if not (author_nodes := self._author_selector(self.precomputed.doc)):
            return []
        else:
            if len(author_nodes) > 1:
                # With more than one entry, we abuse the fact that authors are linked with an <a> tag,
                # but cities are not
                author_nodes = [node for node in author_nodes if bool(next(node.iterchildren(tag="a"), None))]
            return [text for node in author_nodes if "F.A.Z" not in (text := node.text_content())]

    @attribute
    def title(self) -> Optional[str]:
        return self.precomputed.meta.get("og:title")
