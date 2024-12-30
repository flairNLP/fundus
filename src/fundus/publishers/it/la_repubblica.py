from datetime import datetime
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


class LaRepubblicaParser(ParserProxy):
    class V1(BaseParser):
        # Selectors for article body parts
        _paragraph_selector = CSSSelector("div.story__text p")
        _subheadline_selector = CSSSelector("div.story__text h2")

        @attribute
        def title(self) -> Optional[str]:
            # Get the headline from og:title meta tag
            return self.precomputed.meta.get("og:title")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            # Extract article body using utility function
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            # Extract authors from schema.org NewsArticle data
            authors = self.precomputed.ld.xpath_search("//NewsArticle/author")
            if authors:
                return generic_author_parsing(authors)
            return []

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            # Extract publishing date from schema.org NewsArticle data
            date_str = self.precomputed.ld.xpath_search("//NewsArticle/datePublished")
            return generic_date_parsing(date_str[0] if date_str else None)

        @attribute
        def topics(self) -> List[str]:
            # Extract topics from schema.org NewsArticle data
            topics = self.precomputed.ld.xpath_search("//NewsArticle/about")
            if topics:
                return generic_topic_parsing([topic.get("name") for topic in topics if topic.get("name")])
            return []

        @attribute
        def free_access(self) -> bool:
            # Check if article is freely accessible from schema.org NewsArticle data
            is_free = self.precomputed.ld.xpath_search("//NewsArticle/isAccessibleForFree")
            return bool(is_free[0]) if is_free else False
