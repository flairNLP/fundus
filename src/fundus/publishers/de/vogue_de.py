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


class VogueDEParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[@class='body__inner-container'] /p[text()]")
        _subheadline_selector = CSSSelector("div.body__inner-container > h2")
        _summary_selector = XPath("//div[contains(@class, 'ContentHeaderDek')]")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("article:author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath(
                    "//article//*[not(self::a)]/picture[not(contains(@class, 'summary-item__image'))]//img"
                ),
                caption_selector=XPath("./ancestor::figure//span[contains(@class, 'caption__text')]"),
                author_selector=XPath("./ancestor::figure//span[contains(@class, 'caption__credit')]"),
            )
