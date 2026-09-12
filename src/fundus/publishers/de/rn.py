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


class RuhrNachrichtenParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2026, 8, 25)

        _summary_selector = CSSSelector("div.article__content > p.article__teaser-text")
        _paragraph_selector: XPath = CSSSelector("div.article__content > p:not([class])")
        _subheadline_selector = CSSSelector("div.article__content > h2")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("author"))

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
                image_selector=XPath("//figure[not(@class='teaser__thumbnail')]//img"),
                paragraph_selector=self._paragraph_selector,
                caption_selector=XPath("./ancestor::figure//figcaption/text()"),
                author_selector=XPath("./ancestor::figure//figcaption/span"),
            )

    class V1_1(V1):
        _bloat_regex = r"(?i)^verfasst von"

        _paragraph_selector = XPath(
            f"//div[@class='article__content']/p[@class='wp-block-paragraph' and not(re:test(string(), '{_bloat_regex}'))] | "
            "//div[@class='article__content']/ul[@class='wp-block-list']/li",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
