import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class CNBCParser(ParserProxy):
    class V1(BaseParser):
        _subheadline_selector: CSSSelector = CSSSelector("div[data-module = 'ArticleBody'] > h2")
        _paragraph_selector: XPath = XPath("//div[@data-module='ArticleBody'] / div[@class='group'] / p[text()]")
        _key_points_selector: CSSSelector = CSSSelector("div.RenderKeyPoints-list li")

        @attribute
        def body(self) -> ArticleBody:
            body: ArticleBody = extract_article_body_with_selector(
                self.precomputed.doc,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )
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
