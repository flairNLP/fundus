import datetime
from typing import List, Optional

from src.parser.html_parser import ArticleBody, BaseParser, attribute
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class WAZParser(BaseParser):
    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            paragraph_selector=".article__body > p",
            summary_selector=".article__header__intro__text",
            subheadline_selector=".article__body > h3",
        )

    @attribute
    def title(self) -> Optional[str]:
        return self.precomputed.meta.get("og:title")

    @attribute
    def authors(self) -> List[str]:
        return generic_author_parsing(self.precomputed.meta.get("author"))

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.meta.get("datePublished"))
