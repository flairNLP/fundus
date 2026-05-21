import datetime
import re
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class TechRadarParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath("//article//header//*[contains(@class, 'strapline')]")
        _subheadline_selector = XPath(
            "//article//div[contains(concat(' ', normalize-space(@class), ' '), ' text-copy ')]"
            "//*[self::h2 or self::h3][normalize-space()]"
        )

        _bloat_regex = (
            r"^When you purchase through links|"
            r"^Sign up for breaking news|"
            r"^Follow TechRadar on Google News|"
            r"^Get daily insight|"
            r"^You might also like"
        )
        _paragraph_selector = XPath(
            "//article//div[contains(concat(' ', normalize-space(@class), ' '), ' text-copy ')]"
            "//*[self::p or self::li]"
            "[normalize-space() and not(contains(@class, 'vanilla-image-block')) "
            "and not(self::li[contains(@class, 'list-none')]) "
            f"and not(re:test(normalize-space(string()), '{_bloat_regex}'))]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(
                self.precomputed.ld.bf_search("author") or self.precomputed.meta.get("mrf:authors")
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("article:tag"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//article"),
                image_selector=XPath("//article//figure//img"),
                caption_selector=XPath("./ancestor::figure//figcaption"),
                author_selector=re.compile(r"(?i)image credit[s]?: (?P<credits>.*)"),
            )
