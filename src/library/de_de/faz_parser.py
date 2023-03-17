import datetime
from typing import List, Optional

from src.parser.html_parser import ArticleBody, BaseParser, register_attribute
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class FAZParser(BaseParser):
    @register_attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            summary_selector="div.atc-Intro > p",
            subheadline_selector="div.atc-Text > h3",
            paragraph_selector="div.atc-Text > p",
        )

    @register_attribute
    def topics(self) -> Optional[List[str]]:
        return generic_topic_parsing(self.precomputed.meta.get("keywords"))

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

    @register_attribute
    def authors(self) -> List[str]:
        # Unfortunately, the raw data may contain cities. Most of these methods aims to remove the cities heuristically.
        first_author_extraction_attempt = [
            el.text_content() for el in self.precomputed.doc.cssselect(".atc-MetaAuthor")
        ]

        if not first_author_extraction_attempt:
            return []
        if len(first_author_extraction_attempt) == 1:
            # With a single entry we can be sure that it won't contain a city
            return first_author_extraction_attempt
        else:
            # With more than one entry, we abuse the fact that authors are linked, but cities are not
            link_based_extraction = [el.text_content() for el in self.precomputed.doc.cssselect(".atc-MetaAuthorLink")]
            return link_based_extraction

    @register_attribute
    def title(self) -> Optional[str]:
        return self.precomputed.meta.get("og:title")
