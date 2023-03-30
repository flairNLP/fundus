import datetime
from typing import List, Optional

from src.parser.html_parser import ArticleBody, BaseParser, attribute
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class SternParser(BaseParser):
    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            paragraph_selector=".article__body >p",
            summary_selector=".intro__text",
            subheadline_selector=".subheadline-element",
        )

    @attribute
    def authors(self) -> List[str]:
        return generic_author_parsing(self.precomputed.ld.bf_search("author"))

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(
            self.precomputed.meta.get(
                "date",
            )
        )

    @attribute
    def title(self):
        first_title_candidate = self.precomputed.ld.bf_search("headline")
        second_title_candidate = self.precomputed.meta.get("og:title")
        longer_title = max((first_title_candidate, second_title_candidate), key=lambda x: len(x))
        return longer_title

    @attribute
    def topics(self) -> Optional[List[str]]:
        all_topics = generic_topic_parsing(self.precomputed.meta.get("sis-article-keywords"))
        if not all_topics:
            return []
        return all_topics[0].split("|")
