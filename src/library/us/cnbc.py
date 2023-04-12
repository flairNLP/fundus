import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from src.parser.html_parser import ArticleBody, BaseParser, attribute
from src.parser.html_parser.data import TextSequence
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class CNBCParser(BaseParser):
    _key_points_selector: CSSSelector = CSSSelector("div.RenderKeyPoints-list li")

    @attribute
    def body(self) -> ArticleBody:
        body: ArticleBody = extract_article_body_with_selector(
            self.precomputed.doc,
            subheadline_selector="div[data-module = 'ArticleBody'] > h2",
            paragraph_selector="div.group > p",
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
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.get_value_by_key_path(["NewsArticle", "datePublished"]))

    @attribute
    def title(self) -> Optional[str]:
        title: Optional[str] = self.precomputed.ld.get_value_by_key_path(["NewsArticle", "headline"])
        return title

    @attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get("keywords"))

    @attribute(validate=False)
    def key_points(self) -> List[str]:
        return [key_point.text_content() for key_point in self._key_points_selector(self.precomputed.doc)]
