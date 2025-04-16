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


class BusinessInsiderParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2025, 3, 24)

        _summary_selector = CSSSelector("article ul[class^='summary-list'] > li")
        _subheadline_selector = CSSSelector("article h2, div.slideshow-slide-container h2")
        _paragraph_selector = XPath(
            """
            //article 
            //div[contains(@class, 'content-lock-content')] 
            /p[not(contains(@class, 'disclaimer'))] | 
            //article 
            //div[contains(@class, 'content-lock-content')]
            /div[contains(@class, 'premium-content')] 
            /p[not(contains(@class, 'disclaimer'))] | 
            //div[@class='slide-layout clearfix']
            /p[not(contains(@class, 'disclaimer'))]
            """
        )

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
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
            return self.precomputed.meta.get("title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(
                self.precomputed.meta.get("keywords")
                or self.precomputed.ld.bf_search("keywords")
                or self.precomputed.meta.get("news_keywords")
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//article"),
                image_selector=XPath("//figure//img[not(@data-content-type)]"),
                caption_selector=XPath("./ancestor::figure//figcaption/span[@class='image-caption-text']"),
                author_selector=XPath("./ancestor::figure//figcaption/span[@class='image-source-text']"),
            )

    class V2(BaseParser):
        VALID_UNTIL = datetime.date.today()

        _paragraph_selector = XPath("//section[contains(@class, 'post-body-content')]/p")
        _summary_selector = XPath("//div[@class='post-summary-bullets']//li")
        _subheadline_selector = XPath("//section[contains(@class, 'post-body-content')]/h2")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
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
            return self.precomputed.meta.get("title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(
                self.precomputed.meta.get("keywords")
                or self.precomputed.ld.bf_search("keywords")
                or self.precomputed.meta.get("news_keywords")
            )
