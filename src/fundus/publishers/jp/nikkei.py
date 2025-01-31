import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_date_parsing,
    generic_nodes_to_text,
    generic_topic_parsing,
    image_extraction,
)


class NikkeiParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath(
            "//section[@class='container_campx13']//*[self::div and @class='container_c1tzahnc' and position()=1]"
        )
        _paragraph_selector = CSSSelector("section[data-track-article-content] > p")
        _subheadline_selector = CSSSelector("section[data-track-article-content] > div > h2")

        _topic_selector = XPath("//article //header //div[contains(@class, 'topicLink')]")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def topics(self) -> List[str]:
            if topic_nodes := self._topic_selector(self.precomputed.doc):
                return generic_topic_parsing(generic_nodes_to_text(topic_nodes), "・")
            return []

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                lower_boundary_selector=CSSSelector("p.title_thchiij"),
                # https://regex101.com/r/qjEM41/1
                author_selector=re.compile(r"=(?P<credits>[^=]*?)\s*$"),
            )
