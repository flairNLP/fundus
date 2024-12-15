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


class DieWeltParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2024, 8, 12)

        _author_substitution_pattern: Pattern[str] = re.compile(r"WELT")
        _paragraph_selector: XPath = CSSSelector("body .c-article-text > p")
        _summary_selector = CSSSelector("div.c-summary__intro")
        _subheadline_selector = CSSSelector(".c-article-text > h3")

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
            return apply_substitution_pattern_over_list(
                generic_author_parsing(self.precomputed.ld.bf_search("author")), self._author_substitution_pattern
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=CSSSelector("figure:not(.c-inline-video) img"),
                caption_selector=XPath("./ancestor::figure//span[@class='c-content-image__caption-alt']"),
                author_selector=XPath("./ancestor::figure//span[@class='c-content-image__caption-source']"),
                lower_boundary_selector=XPath("//section[@class='c-attached-content']"),
                size_pattern=re.compile(r"-w(?P<width>[0-9]+)/"),
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()

        _summary_selector = CSSSelector("div.c-article-page__intro")
        _subheadline_selector = CSSSelector(".c-rich-text-renderer--article > h3")
        _paragraph_selector = XPath("//div[contains(@class, 'c-rich-text-renderer--article')] /p[text()]")
