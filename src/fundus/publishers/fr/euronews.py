from datetime import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute, utility


class EuronewsParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("p.c-article-summary")
        _subheadline_selector = CSSSelector("div.c-article-content > h2")
        _paragraph_selector = CSSSelector("div.c-article-content > p")

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def body(self) -> ArticleBody:
            article_body = utility.extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )
            return article_body

        @attribute
        def authors(self) -> List[str]:
            key_path = ["NewsArticle", "author", "name"]
            author_string = self.precomputed.ld.get_value_by_key_path(key_path)
            return utility.generic_author_parsing(author_string)

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            date_string = self.precomputed.meta.get("date.available")
            return utility.generic_date_parsing(date_string)

        @attribute
        def topics(self) -> List[str]:
            keyword_string = self.precomputed.meta.get("keywords")
            return utility.generic_topic_parsing(keyword_string)
