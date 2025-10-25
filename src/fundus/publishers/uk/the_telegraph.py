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


class TheTelegraphParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2024, 9, 9)
        _paragraph_selector = CSSSelector("div.articleBodyText p")
        _subheadline_selector = CSSSelector("div.articleBodyText h2")
        _summary_selector = CSSSelector("p[itemprop='description']")
        _datetime_selector = CSSSelector("time[itemprop='datePublished']")

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
        def publishing_date(self) -> Optional[datetime.datetime]:
            datetime_nodes = self._datetime_selector(self.precomputed.doc)
            if datetime_nodes:
                return generic_date_parsing(datetime_nodes[0].get("datetime"))
            return None

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("DCSext.author"))

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
                caption_selector=XPath("./ancestor::figure//figcaption/span[1]"),
                relative_urls=True,
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))
