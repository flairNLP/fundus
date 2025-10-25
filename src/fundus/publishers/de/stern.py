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


class SternParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2024, 10, 26)

        _paragraph_selector = CSSSelector(".article__body >p")
        _summary_selector = CSSSelector(".intro__text")
        _subheadline_selector = CSSSelector(".subheadline-element")

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
            initial_authors = generic_author_parsing(self.precomputed.ld.bf_search("author"))
            return [el for el in initial_authors if el != "STERN.de"]

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(
                self.precomputed.meta.get(
                    "date",
                )
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            topic_nodes = self.precomputed.doc.cssselect(".article__tags li.links__item")
            return [node.text_content().strip("\n ") for node in topic_nodes]

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                image_selector=XPath("//figure[not(contains(@class, 'teaser'))]//img"),
                paragraph_selector=self._paragraph_selector,
                lower_boundary_selector=CSSSelector(".article__tags li.links__item"),
                caption_selector=XPath("./ancestor::figure//figcaption//div[contains(@class,'caption')]"),
                author_selector=XPath("./ancestor::figure//figcaption//div[contains(@class,'credits')]"),
            )

    class V2(BaseParser):
        _paragraph_selector = CSSSelector(".article__body > .text-element > p.is-initial")
        _summary_selector = CSSSelector(".article__body > .intro")
        _subheadline_selector = CSSSelector(".article__body > .subheadline-element")

        _topic_selector = CSSSelector("ul.tags > li")
        _author_selector = CSSSelector("li.authors__list-item > a, li.authors__list-item > .typo-article-info-bold")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(generic_nodes_to_text(self._author_selector(self.precomputed.doc)))

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(
                generic_nodes_to_text(self._topic_selector(self.precomputed.doc), normalize=True)
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                image_selector=XPath("//figure[not(contains(@class, 'teaser'))]//img"),
                paragraph_selector=self._paragraph_selector,
                lower_boundary_selector=self._topic_selector,
                caption_selector=XPath("./ancestor::figure//figcaption//div[contains(@class,'caption')]"),
                author_selector=XPath("./ancestor::figure//figcaption//div[contains(@class,'credits')]"),
            )
