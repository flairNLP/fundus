from datetime import datetime
from typing import List, Optional

from src.parsing import ArticleBody, BaseParser, attribute
from src.parsing.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class TheGatewayPunditParser(BaseParser):
    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            paragraph_selector="div.entry-content > p",
            mode="css",
        )

    @attribute
    def authors(self) -> List[str]:
        return generic_author_parsing(self.precomputed.ld.get_value_by_key_path(["Article", "author"]))

    @attribute
    def publishing_date(self) -> Optional[datetime]:
        return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

    @attribute
    def title(self) -> Optional[str]:
        return self.precomputed.meta.get("og:title")
