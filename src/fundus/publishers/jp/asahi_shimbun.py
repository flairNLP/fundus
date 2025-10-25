import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    apply_substitution_pattern_over_list,
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class AsahiShimbunParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("div.nfyQp > div.bv2Sj > p")
        _paragraph_selector = CSSSelector("div.nfyQp > p")
        _subtitle_selector = CSSSelector("div.nfyQp > h2")

        topic_bloat_pattern = re.compile(r"朝日新聞デジタル|朝日新聞|ニュース|新聞|その他・話題")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subtitle_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("TITLE")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def topics(self) -> List[str]:
            return apply_substitution_pattern_over_list(
                generic_topic_parsing(self.precomputed.meta.get("keywords")), self.topic_bloat_pattern
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                author_selector=re.compile(r"、(?P<credits>[^、]*?)撮影"),
                relative_urls=True,
            )
