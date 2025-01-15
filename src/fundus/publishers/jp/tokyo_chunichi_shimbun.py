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
)


class TokyoChunichiShimbunParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//main//div[@class='block' and not(descendant::div or descendant::h2)]")
        _subheadline_selector = XPath("//main//div[@class='block']//h2")

        _author_bloat_pattern = re.compile(r"記者")
        _topic_bloat_pattern = re.compile(r"話題・|話題")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return apply_substitution_pattern_over_list(
                generic_author_parsing(self.precomputed.ld.bf_search("author")), self._author_bloat_pattern
            )

        @attribute
        def topics(self) -> List[str]:
            if topics := apply_substitution_pattern_over_list(
                generic_topic_parsing(self.precomputed.ld.bf_search("articleSection")), self._topic_bloat_pattern
            ):
                return [topic for topic in topics if "ニュース" not in topic]
            return []

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=CSSSelector("main div.image img, main div.thumb img"),
                caption_selector=XPath(
                    "./ancestor::div[@class='wrap']//p[@class='caption'] | "
                    "./ancestor::div[@class='thumb']//p[@class='thumb-caption']"
                ),
                author_selector=re.compile(r"（(?P<credits>[^）]*?)(撮影)?）\s*$"),
                relative_urls=True,
            )
