import datetime
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    image_extraction,
)


class ABCParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[@class='voc-d ']//p[@class='voc-p']")
        _subheadline_selector = XPath("//div[@class='voc-d ']//h3[@class='voc-d-c__s-title']")
        _summary_selector = XPath("//div[@class='voc-info-container']/h2[text()]")

        _topics_selector = XPath("//div[@class='voc-wrapper']//ul[@class='voc-topics__list']/li[position() > 1]")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("title")

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def topics(self) -> List[str]:
            return [node.text_content().strip() for node in self._topics_selector(self.precomputed.doc)]

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//figure//img[@class='voc-img']"),
                upper_boundary_selector=XPath("//article"),
                caption_selector=XPath(
                    "./ancestor::div[contains(@class, 'voc-img-container')]//figcaption/span[contains(@class,'text')]"
                ),
                author_selector=XPath(
                    "./ancestor::div[contains(@class, 'voc-img-container')]//figcaption/span[contains(@class,'author')]"
                ),
            )
