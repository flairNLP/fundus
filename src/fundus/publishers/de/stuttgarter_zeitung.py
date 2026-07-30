import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_nodes_to_text,
    generic_topic_parsing,
    image_extraction,
)


class StuttgarterZeitungParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2026, 6, 29)

        _paragraph_selector = CSSSelector("div.article-body p")
        _subheadline_selector = CSSSelector("div.article-body h2")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//figure//picture//img"),
                caption_selector=XPath("./ancestor::figure//figcaption"),
                relative_urls=True,
            )

    class V2(BaseParser):
        _summary_selector = XPath(
            "//section[@class='u-article-header']/div/span[not(contains(@class,'u-article-type-flag'))]"
        )
        _paragraph_selector = XPath("//article//p[@class='u-paragraph'] | //article//ul[@class='u-list']/li[text()]")
        _subheadline_selector = XPath("//article//h2[contains(@class,'u-headline')]")

        _topic_selector = XPath("//ul[@class='u-tags__list']//li")

        _bloat_topics = {"alle themen"}

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
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(
                generic_nodes_to_text(self._topic_selector(self.precomputed.doc)), result_filter=self._bloat_topics
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//figure[not(contains(@class, 'teaser'))]//img"),
                caption_selector=XPath("./ancestor::figure//figcaption/p"),
                author_selector=XPath("./ancestor::figure//figcaption/span"),
            )
