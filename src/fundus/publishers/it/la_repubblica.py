import re
from datetime import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class LaRepubblicaParser(ParserProxy):
    class V1(BaseParser):
        # Selectors for article body parts
        _summary_selector = CSSSelector("div.story__summary p")
        _paragraph_selector = CSSSelector("div.story__text p")
        _subheadline_selector = CSSSelector("div.story__text h2")

        @attribute
        def title(self) -> Optional[str]:
            # Get the headline from og:title meta tag
            return self.precomputed.meta.get("og:title")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            # Extract the article body using utility function
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
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
            # Use scalar parameter for direct value
            date_str = self.precomputed.ld.xpath_search("//NewsArticle/datePublished", scalar=True)
            return generic_date_parsing(date_str)

        @attribute
        def topics(self) -> List[str]:
            # Simplified topic extraction using name in xpath
            topics = self.precomputed.ld.xpath_search("//NewsArticle/about/name")
            return generic_topic_parsing(topics) if topics else []

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//figure[not(@class='inline-article__media')]//*[not(self::noscript)]/img"),
                author_selector=re.compile(r"\((foto)?(?P<credits>.*)\)$"),
            )
