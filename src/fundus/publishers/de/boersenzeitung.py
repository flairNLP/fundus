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
    image_extraction,
)


class BoersenZeitungParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2024, 12, 9)

        _paragraph_selector = CSSSelector("storefront-content-body .no-tts p")
        _subheadline_selector = XPath("//p[contains(@class, 'interline')]")
        _summary_selector = CSSSelector("storefront-html.excerpt > div")

        _topic_selector = CSSSelector("a[href^='/thema'] > span")
        _paywall_selector = CSSSelector("storefront-html.paywall-headline > div")

        _title_bloat_pattern = re.compile(r"\|.*")

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
            if fulltitle := self.precomputed.meta.get("og:title"):
                return re.sub(self._title_bloat_pattern, "", fulltitle).strip()
            return None

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("twitter:misc:Written by"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published:time"))

        @attribute
        def topics(self) -> List[str]:
            return [node.text_content().strip() for node in self._topic_selector(self.precomputed.doc)]

        @attribute
        def free_access(self) -> bool:
            # print(self._paywall_selector(self.precomputed.doc).text_content().strip())
            return not [node.text_content().strip() for node in self._paywall_selector(self.precomputed.doc)]

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//h1|//script"),
                image_selector=XPath("//storefront-image|//figure//img"),
                author_selector=XPath("./ancestor::storefront-section//storefront-html[@class='image-copyright']"),
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("twitter:data1"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))
