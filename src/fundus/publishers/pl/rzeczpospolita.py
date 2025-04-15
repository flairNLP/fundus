import datetime
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
    strip_nodes_to_text,
)


class RzeczpospolitaParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            "//div[contains(@class,'article--content')]//div[contains(@class,'body articleBody')]"
            "//p[contains(@class, 'article--paragraph')]"
        )
        _summary_selector = XPath("//div[@class='blog--subtitle ']")
        _subheadline_selector = XPath(
            "//div[contains(@class,'article--content')]//div[contains(@class,'body articleBody')]//h2"
        )

        _topic_selector = XPath("//div[@data-mrf-section='Article / Tags']/a")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            topic_string = strip_nodes_to_text(self._topic_selector(self.precomputed.doc), join_on=",")
            if topic_string is not None:
                return generic_topic_parsing(topic_string, delimiter=",")
            return []

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//div[@class='blog--image']//img"),
                upper_boundary_selector=XPath("//div[@class='row']//h1"),
                caption_selector=XPath("./ancestor::div[@class='blog--image']//p[@class='article--media--lead']"),
                author_selector=XPath("./ancestor::div[@class='blog--image']//p[@class='image--author']"),
            )
