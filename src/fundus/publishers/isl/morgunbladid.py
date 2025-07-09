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


class MorgunbladidParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath("//div[@class='main-layout']//div[@class='is-merking']/p")
        _paragraph_selector = XPath(
            "//div[@class='main-layout' or @data-element-type='body-facts']" "/p[not(a and not(text()))]"
        )
        _subheadline_selector = XPath("//div[@class='main-layout' or @class='et_pb_text_inner']/h3")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                subheadline_selector=self._subheadline_selector,
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
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//div[@class='image']//img"),
                caption_selector=XPath("./ancestor::div[contains(@class, 'newsitem-image')]//span[@class='caption']"),
                author_selector=XPath("./ancestor::div[contains(@class, 'newsitem-image')]//span[@class='credit']"),
            )
