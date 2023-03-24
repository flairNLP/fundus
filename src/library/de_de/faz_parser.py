import datetime
from typing import List, Optional

from src.parser.html_parser import ArticleBody, BaseParser, attribute
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class FAZParser(BaseParser):
    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            summary_selector="div.atc-Intro > p",
            subheadline_selector="div.atc-Text > h3",
            paragraph_selector="div.atc-Text > p",
        )

    @attribute
    def topics(self) -> Optional[List[str]]:
        return generic_topic_parsing(self.precomputed.meta.get("keywords"))

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

    @attribute
    def authors(self) -> List[str]:
        result = []
        # Unfortunately, the raw data may contain cities. Most of these methods aims to remove the cities heuristically.
        first_author_extraction_attempt = [
            el.text_content() for el in self.precomputed.doc.cssselect(".atc-MetaAuthor")
        ]

        if not first_author_extraction_attempt:
            result = []
        if len(first_author_extraction_attempt) == 1:
            # With a single entry we can be sure that it won't contain a city
            result = first_author_extraction_attempt
        else:
            # With more than one entry, we abuse the fact that authors are linked, but cities are not
            link_based_extraction = [el.text_content() for el in self.precomputed.doc.cssselect(".atc-MetaAuthorLink")]
            result = link_based_extraction

        return [el for el in result if "F.A.Z" not in el]

    @attribute
    def title(self) -> Optional[str]:
        return self.precomputed.meta.get("og:title")
