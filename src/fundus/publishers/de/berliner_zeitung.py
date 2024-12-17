import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.data import Image
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class BerlinerZeitungParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("div[id=articleBody] > p")
        _summary_selector = CSSSelector("div[data-testid=article-header] > p")
        _subheadline_selector = CSSSelector("div[id=articleBody] > h2")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("article:author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//div[not(contains(@class, 'author') or contains(@class, 'preview'))]/img"),
                caption_selector=XPath(
                    "./ancestor::div[@class='article_image-container__Yo6Cx']"
                    "//span[@class='article_image-container-caption__lZ5kc']"
                ),
                author_selector=XPath(
                    "./ancestor::div[@class='article_image-container__Yo6Cx']"
                    "//span[@class='article_image-container-source__rbsO4']"
                ),
            )
