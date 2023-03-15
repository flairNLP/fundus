import datetime
from typing import List, Optional

from src.parser.html_parser import ArticleBody, BaseParser, register_attribute
from src.parser.html_parser.utility import (extract_article_body_with_selector,
                                            generic_author_parsing,
                                            generic_date_parsing,
                                            generic_topic_parsing)


class DieWeltParser(BaseParser):
    @register_attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            summary_selector="div.c-summary__intro",
            subheadline_selector=".c-article-text > h3",
            paragraph_selector="body .c-article-text > p",
        )

    @register_attribute
    def authors(self) -> List[str]:
        return generic_author_parsing(self.precomputed.ld.bf_search("author"))

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

    @register_attribute
    def title(self):
        return self.precomputed.ld.bf_search("headline")

    @register_attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get("keywords"))
