import re
from datetime import datetime
from typing import List, Optional

from src.parsing import ArticleBody, BaseParser, attribute
from src.parsing.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class FreeBeaconParser(BaseParser):
    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            paragraph_selector=".article-content > p",
        )

    @attribute
    def authors(self) -> List[str]:
        return generic_author_parsing(self.precomputed.meta.get("author"))

    @attribute
    def publishing_date(self) -> Optional[datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

    @attribute
    def title(self) -> Optional[str]:
        return self.precomputed.ld.bf_search("headline")

    @attribute
    def topics(self) -> List[str]:
        topics: Optional[List[str]] = self.precomputed.ld.bf_search("keywords")
        return topics if topics else []
