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
    generic_topic_parsing,
    image_extraction,
)


class GolemParser(ParserProxy):
    class V1(BaseParser):
        _bloat_regex = r"^Dieser Artikel enthält sogenannte Affiliate-Links"
        _summary_selector = CSSSelector("hgroup > p")
        _paragraph_selector = XPath(
            f"//section /p[not(@class='meta' or re:test(string(), '{_bloat_regex}'))]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _subheadline_selector = CSSSelector("div > section > h2")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            if title := self.precomputed.meta.get("title"):
                return title.replace(" - Golem.de", "")
            else:
                return None

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("news_keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//article"),
                author_selector=re.compile(r"(?i)\(bild:(?P<credits>.*)\)"),
            )
