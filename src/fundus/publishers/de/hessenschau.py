from datetime import datetime
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


class HessenschauParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath(
            "//p[(@class='copytext__text text__copytext'"
            " or contains(@class, 'copytext__paragraph'))"
            " and position()=1] /strong"
        )
        _paragraph_selector = XPath(
            "//p[(@class='copytext__text text__copytext' or contains(@class, 'copytext__paragraph'))"
            " and not(child::strong and position()=1)] | "
            "//ul[contains(@class, 'copytext__paragraph')]/li"
        )
        _subheadline_selector = CSSSelector("h2[class*=head]")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("news_keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//figure[not(@class='ar-1-1')]//*[not(self::noscript)]/img"),
                caption_selector=XPath("./ancestor::figure//span[@class='pr-3']"),
                author_selector=XPath("./ancestor::figure//span[@class='text-gray-scorpion dark:text-text-dark']"),
            )
