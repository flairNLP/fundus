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


class SalzburgerNachrichtenParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2025, 12, 10)

        _paragraph_selector = XPath("//div[contains(@class, 'article-body-text') or contains(@class,'section-text')]/p")
        _subheadline_selector = XPath(
            "//div[contains(@class, 'article-body-text') or contains(@class,'section-text')]//h2"
        )
        _summary_selector = XPath("//p[@class='article-leadtext']")

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
            return self.precomputed.ld.xpath_search("NewsArticle/headline", scalar=True)

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//h1"),
                caption_selector=XPath("./ancestor::figure//div[contains(@class, 'description')]"),
                author_selector=XPath("./ancestor::figure//div[contains(@class, 'copyright')]"),
            )

    class V2(BaseParser):
        _summary_selector = CSSSelector("div.articleContent > p.vorspann")
        _paragraph_selector = XPath(
            r"//div[contains(@class, 'articleText')] /p[not(re:test(string(.), '^\(Quelle:.*\)$'))]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _subheadline_selector = CSSSelector("div.articleText > h2")

        _topic_selector = XPath("//div[@class='articleTags']")

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
            return self.precomputed.ld.xpath_search("NewsArticle/headline", scalar=True)

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
                upper_boundary_selector=XPath("//article"),
                caption_selector=XPath(
                    "./ancestor::figure//figcaption[not(child::div[@class='bildunterschrift'])]/text() |"
                    "./ancestor::figure//figcaption/div[@class='bildunterschrift']"
                ),
                author_selector=XPath("./ancestor::figure//div[@class='bildautor']"),
                lower_boundary_selector=CSSSelector("div.commentOuter"),
                relative_urls=True,
            )
