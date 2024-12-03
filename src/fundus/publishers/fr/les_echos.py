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
    generic_nodes_to_text,
    image_extraction,
    normalize_whitespace,
)


class LesEchosParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("article header > p")
        _subheadline_selector = CSSSelector("article div.post-paywall > h3")

        _bloat_regex_ = r"^\s*Pour ne rien rater de l'actualité politique"

        _paragraph_selector = XPath(
            f'//article //div[contains(@class, "post-paywall")] /p[not(re:test(string(), "{_bloat_regex_}"))]',
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )

        _topic_selector = CSSSelector("header div.sc-108qdzy-3 div.sc-108qdzy-2 > div")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            if title := self.precomputed.meta.get("og:title"):
                return normalize_whitespace(title)
            return None

        @attribute
        def topics(self) -> List[str]:
            topic_nodes = self._topic_selector(self.precomputed.doc)
            return [normalize_whitespace(text) for text in generic_nodes_to_text(topic_nodes)]

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(
                self.precomputed.meta.get("article:published_time") or self.precomputed.ld.bf_search("datePublished")
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                author_selector=re.compile(r"\((?P<credits>.*?)\)$"),
            )
