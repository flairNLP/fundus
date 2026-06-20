import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute, function
from fundus.parser.data import Image
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_nodes_to_text,
    generic_topic_parsing,
    image_extraction,
    transform_breaks_to_tag,
)


class BerlinerZeitungParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2026, 4, 23)

        _paragraph_selector: XPath = CSSSelector("div[id=articleBody] > p")
        _summary_selector: XPath = CSSSelector("div[data-testid=article-header] > p")
        _subheadline_selector: XPath = CSSSelector("div[id=articleBody] > h2")

        _image_selector = XPath("//div[not(contains(@class, 'author') or contains(@class, 'preview'))]/img")
        _author_selector = XPath(
            "./ancestor::div[@class='article_image-container__Yo6Cx']"
            "//span[@class='article_image-container-source__rbsO4']"
        )
        _caption_selector = XPath(
            "./ancestor::div[@class='article_image-container__Yo6Cx']"
            "//span[@class='article_image-container-caption__lZ5kc']"
        )

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
                image_selector=self._image_selector,
                caption_selector=self._caption_selector,
                author_selector=self._author_selector,
            )

    class V2(BaseParser):
        _paragraph_selector = XPath("//article//p[contains(@class, 'leading-7') and text()]")
        _subheadline_selector = XPath("//article//h2")
        _summary_selector = XPath("//article//p[contains(@class, 'font-roboto font-normal')]")

        _image_selector = XPath(
            "//div[not(contains(@class, 'w-[48px] h-[48px]') or contains(@class, 'flex-shrink'))]/img"
        )
        _topic_selector = XPath("//article//a[contains(@href, '/category/')]")
        _author_selector = XPath(
            "./ancestor::div[@class='relative p-4 bg-blue-100' or @class='my-4']//p[contains(@class, 'text-gray-700')]"
        )
        _caption_selector = XPath(
            "./ancestor::div[@class='relative p-4 bg-blue-100' or @class='my-4']//p[contains(@class, 'text-gray-800')]"
        )

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
            return generic_topic_parsing(
                generic_nodes_to_text(self._topic_selector(self.precomputed.doc), normalize=True)
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=self._image_selector,
                caption_selector=self._caption_selector,
                author_selector=self._author_selector,
            )

        @function(priority=1)
        def _preprocess(self) -> None:
            for node in self._paragraph_selector(self.precomputed.doc):
                transform_breaks_to_tag(node, replace=True)
