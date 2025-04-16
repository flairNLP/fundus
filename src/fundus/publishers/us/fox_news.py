import datetime
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


class FoxNewsParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector(".article-meta > h2")
        _paragraph_selector = XPath(
            "(//div[@class='article-body'] | //div[@class='article-body']/div[contains(@class, 'paywall')]) "
            "/p[not(child::script) and text()]"
        )

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("dc.creator"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("classification-tags"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//article//picture//img[not(@*[starts-with(name(), 'data-v-')])]"),
                caption_selector=XPath("(./ancestor::div[@class='image-ct inline']//div[@class='caption']/p/span)[1]"),
                author_selector=XPath(
                    "(./ancestor::div[@class='image-ct inline']//div[@class='caption']/p/span)[last()]"
                ),
            )
