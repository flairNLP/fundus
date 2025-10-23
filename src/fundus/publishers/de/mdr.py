import datetime
import re
from typing import List, Optional, Pattern

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    apply_substitution_pattern_over_list,
    extract_article_body_with_selector,
    generic_date_parsing,
    generic_text_extraction_with_css,
    generic_topic_parsing,
    image_extraction,
)


class MDRParser(ParserProxy):
    class V1(BaseParser):
        _author_substitution_pattern: Pattern[str] = re.compile(r"MDR \w*$|MDR \w*-\w*$|MDRfragt-Redaktionsteam|^von")
        # regex examples: https://regex101.com/r/2DSjAz/1
        _source_detection: str = r"^((MDR (AKTUELL ){0,1}\(([A-z]{2,3}(\/[A-z]{2,3})*|[A-z, ]{2,50}))\)|(Quell(e|en): (u.a. ){0,1}[A-z,]{3,4})|[A-z]{2,4}(, [A-z]{2,4}){0,3}( \([A-z]{2,4}\)){0,1}$|[A-z]{2,4}\/[A-z(), \/]{3,10}$)"
        _paragraph_selector = XPath(
            f"//div[contains(@class, 'paragraph')]"
            f"/p[not(re:test(em, '{_source_detection}') or re:test(text(), '{_source_detection}'))]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _summary_selector = CSSSelector("p.einleitung")
        _subheadline_selector = CSSSelector("div > h3.subtitle")
        _author_selector = CSSSelector(".articleMeta > .author")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def topics(self) -> List[str]:
            if self.precomputed.meta.get("news_keywords") is not None:
                return generic_topic_parsing(self.precomputed.meta.get("news_keywords"))
            else:
                return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            if raw_author_str := generic_text_extraction_with_css(self.precomputed.doc, self._author_selector):
                raw_author_str = raw_author_str.replace(" und ", ", ")
                author_list = [name.strip() for name in raw_author_str.split(",")]
                return apply_substitution_pattern_over_list(author_list, self._author_substitution_pattern)

            return []

        @attribute
        def title(self) -> Optional[str]:
            return title if isinstance(title := self.precomputed.ld.bf_search("headline"), str) else None

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//div[@id='content']"),
                image_selector=XPath("//div[contains(@class,'mediaCon ') and not(@data-ctrl-player)]//noscript/img"),
                caption_selector=XPath("./ancestor::div[@class='media mediaA ']//span[@class='mediaSubtitle']"),
                author_selector=XPath("./ancestor::div[@class='media mediaA ']//span[@class='mediaRights copyright']"),
            )
