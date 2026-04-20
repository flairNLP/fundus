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


class DailyStarParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2026, 4, 9)

        _summary_selector: XPath = CSSSelector("p.sub-title")
        _paragraph_selector = XPath("//div[@class='article-body'] /p[text()]")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("author"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=CSSSelector("figure.in-article-image img"),
                caption_selector=XPath("./ancestor::figure//figcaption/span[@class='caption']"),
                author_selector=XPath("./ancestor::figure//figcaption/span[@class='credit']"),
            )

    class V1_1(V1):
        _summary_selector = XPath("//h2[@data-testid='leadtext']")
        _subheadline_selector = XPath("//h3[contains(@class, 'heading-three')]")
        _paragraph_selector = XPath("//ul[@data-tmdatatrack='content-unit']/li | " "//article/p[text()]")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                caption_selector=XPath("./ancestor::div[contains(@class, 'ImageEmbed_image-embed')]//figcaption/p"),
                author_selector=re.compile(r"(?i)\(image:(?P<credits>.*)\)$"),
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.xpath_search("//NewsArticle/headline", scalar=True)
