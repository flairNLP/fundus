import datetime
from typing import List, Optional

from src.parser.html_parser import ArticleBody, BaseParser, attribute
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class FoxNewsParser(BaseParser):
    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            paragraph_selector=".article-body > p",
        )

    @attribute
    def authors(self) -> List[str]:
        return generic_author_parsing(self.precomputed.meta.get("dc.creator"))

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.get("datePublished"))

    @attribute
    def title(self):
        return self.precomputed.ld.get("headline")

    @attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get("classification-tags"))
