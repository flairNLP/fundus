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


class DailyStarParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("p.sub-title")
        _paragraph_selector = XPath("//div[@class='article-body'] /p[text()]")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("author"))

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
                image_selector=CSSSelector("figure.in-article-image img"),
                caption_selector=XPath("./ancestor::figure//figcaption/span[@class='caption']"),
                author_selector=XPath("./ancestor::figure//figcaption/span[@class='credit']"),
            )
