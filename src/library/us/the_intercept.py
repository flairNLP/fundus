from datetime import datetime
from typing import List, Optional

from src.parser.html_parser import ArticleBody, BaseParser, attribute
from src.parser.html_parser.data import TextSequence
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class TheInterceptParser(BaseParser):
    @attribute
    def body(self) -> ArticleBody:
        body: ArticleBody = extract_article_body_with_selector(
            self.precomputed.doc,
            subheadline_selector="div.PostContent > div > h2",
            # The Intercept uses `p` tags for the article's paragraphs, image captions and photo grid descriptions.
            # Since we are only interested in the article's paragraphs,
            # we exclude the other elements from the paragraph selector.
            # Example article: https://theintercept.com/2023/04/01/israel-palestine-apartheid-settlements/
            paragraph_selector="div.PostContent > div > p:not(p.caption):not(p.PhotoGrid-description)",
            mode="css",
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
        title: str = self.precomputed.ld.get_value_by_key_path(["NewsArticle", "headline"])
        return title

    @attribute
    def topics(self) -> List[str]:
        # The Intercept specifies the article's topics, including other metadata,
        # inside the "keywords" linked data indicated by a "Subject: " prefix.
        # Example keywords: ["Day: Saturday", ..., "Subject: World", ...]
        return [
            keyword[9:]  # Strip "Subject: "
            for keyword in self.precomputed.ld.get_value_by_key_path(["NewsArticle", "keywords"])
            if keyword.startswith("Subject: ")
        ]
