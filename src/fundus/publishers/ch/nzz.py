import datetime
import re
from typing import List, Optional, Pattern

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.data import Image
from fundus.parser.utility import (
    apply_substitution_pattern_over_list,
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    image_extraction,
)


class NZZParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("div.headline p.headline__lead")
        _subheadline_selector = CSSSelector("div.article h2.subtitle, div.article h5.articlecomponent")
        _paragraph_selector = CSSSelector(
            "div.article section[data-nzz-tid='article'] p.articlecomponent:not(.footnote), "
            "div.article div.articlecomponent:not(.content-table) li"
        )

        _author_substitution_pattern: Pattern[str] = re.compile(r"\(.+\)$")

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
                generic_author_parsing(self.precomputed.ld.bf_search("author")),
                pattern=self._author_substitution_pattern,
                replacement="",
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("date"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("title")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                caption_selector=XPath("./ancestor::figure//h2"),
                author_selector=XPath("./ancestor::figure//div[@class='image-description__author']"),
                upper_boundary_selector=CSSSelector("div#page"),
                lower_boundary_selector=XPath("//div[@class='sharebox']"),
            )
