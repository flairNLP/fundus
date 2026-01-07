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


class TheMirrorParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2024, 7, 26)
        _paragraph_selector = XPath(
            "/html/body/main/article/div[@class='article-body']/p[text()] | //div[@class='article-body']//div[@class='live-event-lead-entry']/p[text()] | //div[@class='article-body']//div[@class='entry-content']/p[text()]"
        )
        _summary_selector = XPath("/html/body/main/article/div[@class='lead-content']/p")
        _subheadline_selector = XPath(
            "//div[@class='article-body']/h3 | //div[@class='article-body']//div[@class='entry-content']/h3"
        )

        @attribute
        def body(self) -> Optional[ArticleBody]:
            body = extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )
            return body

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("parsely-pub-date"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("author"))

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=CSSSelector("div.image > img, div.image-container amp-img"),
                caption_selector=XPath(
                    "./ancestor::div[@class='lead-content' or @class='image-container']//figcaption//span[1]"
                ),
                author_selector=XPath(
                    "./ancestor::div[@class='lead-content' or @class='image-container']//figcaption//span[2]"
                ),
                lower_boundary_selector=CSSSelector("reach-viafoura-comments"),
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.date(2025, 11, 19)

        _datetime_selector = CSSSelector("div.article-information[itemprop='datePublished']")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            if date_nodes := self._datetime_selector(self.precomputed.doc):
                return generic_date_parsing(date_nodes[0].attrib.get("content"))
            return None

    class V1_2(V1_1):
        VALID_UNTIL = datetime.date.today()

        _bloat_regex: str = "^Like this story?|^Join our new WhatsApp"

        _summary_selector = XPath("//article[@id='article-body'] /h2[contains(@class, 'lead-text')]")
        _paragraph_selector = XPath(
            f"//article[@id='article-body']"
            f"/p[contains(@class, 'paragraph-text') and not(re:test(string(.), '{_bloat_regex}'))]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _subheadline_selector = XPath("//article[@id='article-body'] /h3 | //article[@id='article-body'] /h4")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                lower_boundary_selector=CSSSelector("reach-recirculation"),
                caption_selector=XPath(
                    "./ancestor::div[contains(@class, 'ImageEmbed')]//figcaption//span[contains(@class, 'caption-title')]"
                ),
                author_selector=XPath(
                    "./ancestor::div[contains(@class, 'ImageEmbed')]//figcaption//span[contains(@class, 'caption-credit')]"
                ),
            )
