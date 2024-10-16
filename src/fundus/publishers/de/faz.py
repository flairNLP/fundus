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
    parse_title_from_root,
    strip_nodes_to_text,
)


class FAZParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2024, 4, 15)

        _paragraph_selector = CSSSelector("div.atc-Text > p")
        _summary_selector = CSSSelector("div.atc-Intro > p")
        _subheadline_selector = CSSSelector("div.atc-Text > h3")
        _author_selector = CSSSelector(".atc-MetaAuthor")

        @attribute
        def body(self) -> Optional[ArticleBody]:
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
                    author_nodes = [node for node in author_nodes if next(node.iterchildren(tag="a"), None) is not None]
                return [text for node in author_nodes if "F.A.Z" not in (text := node.text_content())]

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

    class V2(BaseParser):
        _summary_selector = CSSSelector("div.header-teaser")
        _paragraph_selector = CSSSelector(".body-elements__paragraph")
        _subheadline_selector = CSSSelector("div.body-elements > h3")

        _author_meta_selector = CSSSelector("div.author-meta")
        _topic_selector = XPath("//div[text()=' Schlagworte: '] /a")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def topics(self) -> List[str]:
            topic_string = strip_nodes_to_text(self._topic_selector(self.precomputed.doc), join_on=",")
            if topic_string is not None:
                topic_string = topic_string.replace(",Alle Themen", "")
                return generic_topic_parsing(topic_string, delimiter=",")
            return []

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            if self._author_meta_selector(self.precomputed.doc):
                return generic_author_parsing(self.precomputed.ld.bf_search("author"))
            return []

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title") or parse_title_from_root(self.precomputed.doc)
