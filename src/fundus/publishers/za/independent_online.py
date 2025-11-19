import datetime
import re
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


class IndependentOnlineParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[@class='article_content__Ag4R_']//div[@class='text_text__oJhZK']/p ")

        _topics_selector = XPath("//div[@class='tags_tags__zi1sf']/a")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
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
            topic_string = strip_nodes_to_text(self._topics_selector(self.precomputed.doc), join_on=",")
            if topic_string is not None:
                return generic_topic_parsing(topic_string, delimiter=",")
            return generic_topic_parsing(self.precomputed.meta.get("keywords", []))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//h1"),
                lower_boundary_selector=XPath("//aside[@class='article_sidebar__qgf5d']"),
                image_selector=XPath("//div[contains(@class, 'image')]//img"),
                caption_selector=XPath("./ancestor::div[@class='image_image-widget__LYZT4']//p"),
                author_selector=re.compile(r"(?i)image:(?P<credits>.+)"),
            )
