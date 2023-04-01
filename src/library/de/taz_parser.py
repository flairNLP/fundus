import datetime
from typing import List, Optional

from src.parser.html_parser import ArticleBody, BaseParser, attribute
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class TazParser(BaseParser):
    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            paragraph_selector=".sectbody > p[class*='article']",
            subheadline_selector=".sectbody > h6",
            summary_selector=".intro"
        )

    @attribute
    def title(self) -> Optional[str]:
        return self.precomputed.meta.get("taz:title")

    @attribute
    def authors(self) -> List[str]:
        return generic_author_parsing(self.precomputed.meta.get("author"))

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

    @attribute
    def topics(self) -> Optional[List[str]]:
        return generic_topic_parsing(self.precomputed.meta.get("keywords"))
