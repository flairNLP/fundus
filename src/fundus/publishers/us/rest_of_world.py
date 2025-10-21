from datetime import date, datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    image_extraction,
)


class RestOfWorldParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = date.today()

        _summary_selector: CSSSelector = CSSSelector("div.post-subheader__summary li, p.post-header__text__dek")
        _paragraph_selector: CSSSelector = CSSSelector("div.post-content > p")
        _subheadline_selector: CSSSelector = CSSSelector("div.post-content > h2")

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
            return generic_author_parsing(self.precomputed.ld.xpath_search("NewsArticle/author"))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.ld.xpath_search("NewsArticle/datePublished", scalar=True))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.xpath_search("NewsArticle/headline", scalar=True)

        @attribute
        def topics(self) -> List[str]:
            keywords: List[str] = self.precomputed.ld.xpath_search("NewsArticle/keywords")
            return [keyword for keyword in keywords if not keyword.startswith("Subject: ")]

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//figure//img | //img[@src or @data-src]"),
                caption_selector=XPath("./ancestor::figure//*[self::figcaption or contains(@class, 'caption')]"),
                author_selector=XPath(
                    "(./ancestor::figure//*[contains(@class, 'credit') or contains(@class, 'byline')])[last()]"
                ),
                relative_urls=True,
            )
