from datetime import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute, utility


class KrautreporterParser(ParserProxy):
    class V1(BaseParser):
        _bloat_pattern: str = (
            "^Redaktion:|^Dieser Artikel ist eine Übersetzung|^Übersetzung:|^Recherche:|^Schlussredaktion:"
        )

        _summary_selector = CSSSelector("p[data-test='article-teaser']")
        _subheadline_selector = CSSSelector("div.article-markdown > h2")
        _paragraph_selector = XPath(
            f"//div[contains(@class, 'article-markdown')] /p[not(re:test(string(), '{_bloat_pattern}'))]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )

        _topic_selector = XPath("string(//div[contains(@class, 'article-headers') and contains(@class, 'topic')])")

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
            author_string = self.precomputed.meta.get("author")
            return utility.generic_author_parsing(author_string)

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            key_path = ["NewsArticle", "datePublished"]
            date_string = self.precomputed.ld.get_value_by_key_path(key_path)
            return utility.generic_date_parsing(date_string)

        @attribute
        def topics(self) -> List[str]:
            return utility.generic_topic_parsing(self._topic_selector(self.precomputed.doc))
