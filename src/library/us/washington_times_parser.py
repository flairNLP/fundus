import datetime
from typing import List, Optional

from src.parsing import BaseParser, attribute
from src.parsing.data import ArticleBody, ArticleSection, LinkedDataMapping

__all__ = [
    "BaseParser",
    "attribute",
    "function",
    "ArticleBody",
    "ArticleSection",
    "LinkedDataMapping",
]

from src.parsing.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class WashingtonTimesParser(BaseParser):
    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            paragraph_selector=".bigtext > p",
        )

    @attribute
    def authors(self) -> List[str]:
        return generic_author_parsing(self.precomputed.ld.bf_search("author"))

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

    @attribute
    def title(self) -> Optional[str]:
        return self.precomputed.ld.bf_search("headline")
