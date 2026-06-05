import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import BaseParser, Image, ParserProxy
from fundus.parser.base_parser import attribute
from fundus.parser.data import ArticleBody
from fundus.parser.utility import (
    apply_substitution_pattern_over_list,
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_nodes_to_text,
    generic_topic_parsing,
    image_extraction,
)


class MediaIndonesiaParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[@class='article']/p[(text() or span) and not(@class)]")
        _subheadline_selector = XPath(
            "//div[@class='article']/*[(self::p and (not(text() or @class) and strong)) or self::h2]"
        )

        _author_selector = CSSSelector("div.info > div.author-2")

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
            return apply_substitution_pattern_over_list(
                generic_author_parsing(generic_nodes_to_text(self._author_selector(self.precomputed.doc))),
                pattern=re.compile(r"^Media Indonesia$"),
                replacement="",
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//h1"),
                author_selector=re.compile(r"\((?P<credits>[^(]+)\)$"),
            )
