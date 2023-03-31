import datetime
from typing import List, Optional

from src.parser.html_parser import ArticleBody, BaseParser, attribute
from src.parser.html_parser.utility import (
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
        return generic_author_parsing(self.precomputed.ld.get("author"))

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.get("datePublished"))

    @attribute
    def title(self) -> Optional[str]:
        return self.precomputed.ld.get("headline")
