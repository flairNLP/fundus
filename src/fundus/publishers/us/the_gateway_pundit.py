from datetime import date, datetime
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_nodes_to_text,
    image_extraction,
)


class TheGatewayPunditParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = date(2026, 5, 27)

        _related = r"^Click\s$"
        _paragraph_selector = XPath(
            f"(//div[@class='entry-content'] | //div[@class='entry-content']/blockquote[not(@class='twitter-tweet')]) "
            f"/p[not(child::img or child::script or re:test(text(), '{_related}')) and text()]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.xpath_search("Article/author"))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def title(self) -> Optional[str]:
            if (title := self.precomputed.meta.get("og:title")) is not None:
                title = title.split("|")[0].strip()
            return title

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//div[@class='entry-content']//img"),
                author_selector=XPath("./ancestor::figure//figcaption"),
            )

    class V2(BaseParser):
        _related = (
            r"(?i)^(Click|This article appeared originally|(read )?more:|watch:|more from .{1,20}:|this video is)\s*"
        )
        _author_selector = XPath("//span[@class='author-name']")

        _summary_selector = XPath(
            f"//article//p[not(text())]/strong[text() and not(re:test(text(), '{_related}'))] |"
            f"//div[@class='entry-content']/h3",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _paragraph_selector = XPath(
            f"(//div[@class='entry-content'] | //div[@class='entry-content']/blockquote[not(@class='twitter-tweet')]) "
            f"/p[not(child::img or child::script or re:test(text(), '{_related}')) and text()] |"
            f"//div[@class='entry-content']//ul/li[not(@class)] |"
            f"//div[@class='entry-content']//p[not(text())]/em",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.xpath_search("Article/headline", scalar=True)

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(generic_nodes_to_text(self._author_selector(self.precomputed.doc)))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//div[@class='entry-content']//img"),
                author_selector=XPath("./ancestor::figure//figcaption"),
            )
