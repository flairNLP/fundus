import datetime
import re
from typing import List, Optional

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
    normalize_whitespace,
)


class MainichiShimbunParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("#articledetail-body > p")
        _subheadline_selector = CSSSelector("#articledetail-body > h2")

        _topic_bloat_pattern = re.compile("速報")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            if (title := self.precomputed.meta.get("title")) is not None:
                return normalize_whitespace(title)
            return None

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("cXenseParse:author"))

        @attribute
        def topics(self) -> List[str]:
            return apply_substitution_pattern_over_list(
                generic_topic_parsing(self.precomputed.meta.get("keywords"), delimiter=[",", "・"]),
                self._topic_bloat_pattern,
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//figure//img[not(ancestor::a[contains(@class,'articledetail-image-scale')])]"),
                upper_boundary_selector=CSSSelector("#main"),
                # https://regex101.com/r/awU0Rq/1
                author_selector=re.compile(r"(、|＝(?=.*?撮影$))(?P<credits>[^、]*?)(撮影)?\s*$"),
                relative_urls=True,
            )
