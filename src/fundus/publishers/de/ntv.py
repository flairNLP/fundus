import datetime
import re
from typing import List, Optional, Pattern

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    apply_substitution_pattern_over_list,
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class NTVParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2024, 8, 1)
        _author_substitution_pattern: Pattern[str] = re.compile(r"n-tv NACHRICHTEN")
        _summary_selector = XPath("//div[@class='article__text']/p[not(last()) and strong][1]")
        _paragraph_selector = XPath(
            "//div[@class='article__text']" "/p[not(strong) or (strong and (position() > 1 or last()))]"
        )
        _subheadline_selector: XPath = CSSSelector(".article__text > h2")

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
            initial_list = generic_author_parsing(self.precomputed.meta.get("author"))
            return apply_substitution_pattern_over_list(initial_list, self._author_substitution_pattern)

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("date"))

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
                image_selector=XPath("//figure[not(contains(@class, 'teaser'))]//picture/img"),
                upper_boundary_selector=XPath("//article[@class='article']"),
                caption_selector=XPath("./ancestor::figure//figcaption/p[@class='article__caption']"),
                author_selector=XPath("./ancestor::figure//figcaption/p[@class='article__credit']"),
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.date(2025, 11, 5)
        _author_selector = XPath("string(//span[@class='article__author'])")

        @attribute(deprecated=VALID_UNTIL + datetime.timedelta(days=1))
        def authors(self) -> List[str]:
            author_text: str = self._author_selector(self.precomputed.doc)
            return generic_author_parsing(author_text.replace("Von", ""))

    class V1_2(V1_1):
        VALID_UNTIL = datetime.date.today()

        _summary_selector = XPath("//div[@class='wrapper-article'] //p[contains(@class, 'leadtext')]")
        _paragraph_selector = XPath("//div[@class='wrapper-article'] //p[contains(@class, 'paragraph')]")
        _subheadline_selector = XPath("//div[@class='wrapper-article'] //h2[contains(@class, 'subheadline')]")

        _image_author_pattern: Pattern[str] = re.compile("")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//article"),
                caption_selector=XPath("./ancestor::figure//figcaption"),
                author_selector=re.compile(r"(?P<credits>\([^(^)]*\))$"),
            )
