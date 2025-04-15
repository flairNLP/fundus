import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
    parse_title_from_root,
    strip_nodes_to_text,
)


class NetzpolitikOrgParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("div.entry-content p")
        _summary_selector = CSSSelector("div.entry-excerpt > p")
        _subheadline_selector = CSSSelector("div.entry-content > h3")
        _author_selector = CSSSelector("span > a[rel='author']")
        _topic_selector = CSSSelector("div.entry-footer__tags li")

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title") or parse_title_from_root(self.precomputed.doc)

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
                return generic_topic_parsing(topic_string, delimiter=",")
            return []

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def authors(self) -> List[str]:
            return [node.text_content() for node in (self._author_selector(self.precomputed.doc) or [])]

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                caption_selector=XPath("./ancestor::figure//figcaption/text()"),
                author_selector=XPath("./ancestor::figure//figcaption/span"),
            )
