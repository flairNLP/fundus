from datetime import datetime
from typing import List, Optional

from fundus.parser import ArticleBody, BaseParser, attribute
from fundus.parser.data import TextSequence
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)
from lxml.cssselect import CSSSelector


class TheNewYorkerParser(BaseParser):
    _paragraph_selector = CSSSelector("div.body__inner-container > p")

    @attribute
    def body(self) -> ArticleBody:
        body: ArticleBody = extract_article_body_with_selector(
            self.precomputed.doc,
            paragraph_selector=self._paragraph_selector,
        )
        # The New Yorker has two kinds of descriptions, one in the meta and one in the jd+json.
        # We use the description from the meta since it's the one rendered in the article.
        # Although, sometimes the description is not rendered at all.
        # Parsing the description directly from the article body is very challenging.
        description: Optional[str] = self.precomputed.meta.get("og:description")
        if description is not None:
            body.summary = TextSequence(texts=(description,))
        return body

    @attribute(validate=False)
    def alternative_summary(self) -> Optional[str]:
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
