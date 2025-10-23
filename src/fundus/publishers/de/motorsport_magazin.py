import datetime
import re
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


class MotorSportMagazinParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector: CSSSelector = CSSSelector("section.article-body > p")
        _summary_selector: CSSSelector = CSSSelector("p.teaser")
        _subheadline_selector: CSSSelector = CSSSelector("section.article-body > h2")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def topics(self) -> List[str]:
            if self.precomputed.meta.get("news_keywords") is not None:
                return generic_topic_parsing(self.precomputed.meta.get("news_keywords"))
            else:
                return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//*[not(self::figure)]/picture//img"),
                caption_selector=XPath("(./ancestor::picture/following-sibling::figcaption)[1]"),
                author_selector=re.compile(r"(?i),?\s*foto:(?P<credits>.+)"),
                relative_urls=True,
            )
