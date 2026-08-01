import re
from datetime import date, datetime
from typing import List, Optional, Pattern, Union

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class AftonbladetParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = date(2026, 7, 9)

        _summary_selector = XPath("//p[contains(@data-test-tag,'lead-text')]")
        _paragraph_selector = XPath(
            "//p[starts-with(@class,'hyperion-css-') and not(contains(@data-test-tag,'lead-text'))]"
        )
        _subheadline_selector = XPath("//h2[@data-test-tag='paragraph-header']")

        _caption_selector = XPath("./ancestor::figure//figcaption/span[@class='image-caption']")
        _image_author_selector: Union[XPath, Pattern[str]] = XPath(
            "./ancestor::figure//figcaption/span[contains(@class,'image-byline')]"
        )
        _image_selector = XPath("//figure//img")

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                image_selector=self._image_selector,
                paragraph_selector=self._paragraph_selector,
                caption_selector=self._caption_selector,
                author_selector=self._image_author_selector,
            )

    class V1_1(V1):
        _summary_selector = XPath("(//header)[2]/p")
        _paragraph_selector = XPath(
            "(//section[@class='article-body'])[1]/p | (//section[@class='article-body'])[1]/ul/li"
        )
        _subheadline_selector = XPath("(//section[@class='article-body'])[1]/h2")

        _caption_selector = XPath("./ancestor::figure//figcaption/span[not(contains(@class,'showMore'))]")
        _image_author_selector = re.compile(r"(?i)foto:\s*(?P<credits>.*)\s*$")
        _image_selector = XPath("//figure[contains(@class, 'layout-component')]//img")
