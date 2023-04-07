from datetime import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from src.parser.html_parser import ArticleBody, BaseParser, attribute
from src.parser.html_parser.data import TextSequence
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class TheInterceptParser(BaseParser):
    _paragraph_selector = CSSSelector("div.PostContent > div > p:not(p.caption):not(p.PhotoGrid-description)")
    _subheadline_selector = CSSSelector("div.PostContent > div > h2")

    @attribute
    def body(self) -> ArticleBody:
        body: ArticleBody = extract_article_body_with_selector(
            self.precomputed.doc,
            subheadline_selector=self._subheadline_selector,
            # The Intercept uses `p` tags for the article's paragraphs, image captions and photo grid descriptions.
            # Since we are only interested in the article's paragraphs,
            # we exclude the other elements from the paragraph selector.
            # Example article: https://theintercept.com/2023/04/01/israel-palestine-apartheid-settlements/
            paragraph_selector=self._paragraph_selector,
        )
        description: Optional[str] = self.precomputed.meta.get("og:description")
        if description is not None:
            body.summary = TextSequence(texts=(description,))
        return body

    @attribute
    def authors(self) -> List[str]:
        return generic_author_parsing(self.precomputed.ld.get_value_by_key_path(["NewsArticle", "author"]))

    @attribute
    def publishing_date(self) -> Optional[datetime]:
        return generic_date_parsing(self.precomputed.ld.get_value_by_key_path(["NewsArticle", "datePublished"]))

    @attribute
    def title(self) -> Optional[str]:
        return self.precomputed.ld.get_value_by_key_path(["NewsArticle", "headline"])

    @attribute
    def topics(self) -> List[str]:
        # The Intercept specifies the article's topics, including other metadata,
        # inside the "keywords" linked data indicated by a "Subject: " prefix.
        # Example keywords: ["Day: Saturday", ..., "Subject: World", ...]
        keywords: Optional[List[str]] = self.precomputed.ld.get_value_by_key_path(["NewsArticle", "keywords"])
        if keywords is None:
            return []

        return [keyword[9:] for keyword in keywords if keyword.startswith("Subject: ")]
