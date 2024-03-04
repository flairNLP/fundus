from datetime import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class TheNewYorkerParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath("//div[contains(@class, 'ContentHeaderDek')]")
        _paragraph_selector = CSSSelector("div.body__inner-container > p")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute(validate=False)
        def description(self) -> Optional[str]:
            return self.precomputed.meta.get("og:description")

        @attribute(validate=False)
        def alternative_description(self) -> Optional[str]:
            return self.precomputed.ld.get_value_by_key_path(["NewsArticle", "description"])

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.get_value_by_key_path(["NewsArticle", "author"]))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.ld.get_value_by_key_path(["NewsArticle", "datePublished"]))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.get_value_by_key_path(["NewsArticle", "headline"])

        @attribute(validate=False)
        def alternative_title(self) -> Optional[str]:
            return self.precomputed.ld.get_value_by_key_path(["NewsArticle", "alternativeHeadline"])

        @attribute
        def topics(self) -> List[str]:
            # The New Yorker has keywords in the meta as well as the ld+json.
            # Since the keywords from the meta seem of higher quality, we use these.
            # Example:
            # meta:    ['the arctic', 'ice', 'climate change']
            # ld+json: ['the control of nature', 'the arctic', 'ice', 'climate change', 'splitscreenimagerightinset', 'web']
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute(validate=False)
        def section(self) -> Optional[str]:
            return self.precomputed.ld.get_value_by_key_path(["NewsArticle", "articleSection"])
