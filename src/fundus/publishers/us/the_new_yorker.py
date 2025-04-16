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


class TheNewYorkerParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath("//div[contains(@class, 'ContentHeaderDek')]")
        _paragraph_selector = CSSSelector("div.body__inner-container > p")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute(validate=False)
        def description(self) -> Optional[str]:
            return self.precomputed.meta.get("og:description")

        @attribute(validate=False)
        def alternative_description(self) -> Optional[str]:
            return self.precomputed.ld.xpath_search("NewsArticle/description", scalar=True)

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.xpath_search("NewsArticle/author"))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.ld.xpath_search("NewsArticle/datePublished", scalar=True))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.xpath_search("NewsArticle/headline", scalar=True)

        @attribute(validate=False)
        def alternative_title(self) -> Optional[str]:
            return self.precomputed.ld.xpath_search("NewsArticle/alternativeHeadline", scalar=True)

        @attribute
        def topics(self) -> List[str]:
            # The New Yorker has keywords in the meta as well as the ld+json.
            # Since the keywords from the meta seem of higher quality, we use these.
            # Example:
            # meta:    ['the arctic', 'ice', 'climate change']
            # ld+json: ['the control of nature', 'the arctic', 'ice', 'climate change', 'splitscreenimagerightinset', 'web']
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute(validate=False)
        def section(self) -> Optional[str]:
            return self.precomputed.ld.xpath_search("NewsArticle/articleSection", scalar=True)

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//picture//img"),
                caption_selector=XPath(
                    "./ancestor::*[self::figure or self::header]//*[(self::span and contains(@class, 'caption__text')) or (self::div and contains(@class, '__caption'))]"
                ),
                author_selector=XPath(
                    "(./ancestor::*[self::figure or self::header]//*[(self::span and contains(@class, 'caption__credit')) or (self::div and contains(@class, '__credit'))])[last()]"
                ),
            )
