import datetime
from typing import List, Optional

from src.parser.html_parser import ArticleBody, BaseParser, attribute
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class MerkurParser(BaseParser):
    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            summary_selector="p.id-StoryElement-leadText",
            subheadline_selector="h2.id-StoryElement-crosshead",
            paragraph_selector="p.id-StoryElement-paragraph, article > ul > li",
        )

    @attribute
    def authors(self) -> Optional[List[str]]:
        return generic_author_parsing(self.precomputed.ld.bf_search("author"))

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

    @attribute
    def title(self) -> Optional[str]:
        return self.precomputed.meta.get("og:title")
