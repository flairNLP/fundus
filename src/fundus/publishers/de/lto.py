import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    apply_substitution_pattern_over_list,
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_nodes_to_text,
    generic_topic_parsing,
    image_extraction,
    strip_nodes_to_text,
)


class LTOParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            "//div[@class='article-text-wrapper']/p[text() or child::span[@class='block-align-center']]"
        )
        _summary_selector = CSSSelector("div.reader__intro")
        _subheadline_selector = CSSSelector("div.article-text-wrapper > h2, div.article-text-wrapper > h3")

        _topic_selector = XPath("//ul[@id='articleTags']//li")
        _author_selector = XPath("//p[@class='reader__meta-info'][1]")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def authors(self) -> List[str]:
            return apply_substitution_pattern_over_list(
                generic_author_parsing(strip_nodes_to_text(self._author_selector(self.precomputed.doc))),
                pattern=re.compile("^Gastbeitrag von |^von "),
                replacement="",
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("date"))

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(
                generic_nodes_to_text(self._topic_selector(self.precomputed.doc), normalize=True)
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                author_selector=re.compile(r"(?i)foto:\s*(?P<credits>.+)$"),
                upper_boundary_selector=XPath("//h1"),
                relative_urls=True,
            )
