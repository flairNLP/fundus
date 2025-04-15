import re
from datetime import datetime
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class CorriereDellaSeraParser(ParserProxy):
    class V1(BaseParser):
        # Selectors for article body parts
        _summary_selector = XPath("//p[contains(@class, 'summary')]")
        _paragraph_selector = XPath("//p[@class='chapter-paragraph' and text()]")
        _subheadline_selector = XPath("//h2[contains(@class, 'native-summary-content')]")

        @attribute
        def title(self) -> Optional[str]:
            # Get the headline from og:title meta tag
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            # Extract article body using utility function
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
            breadcrumb_items = self.precomputed.ld.xpath_search("//BreadcrumbList/itemListElement/*/name")
            if breadcrumb_items:
                return generic_topic_parsing(breadcrumb_items[1:])
            section = self.precomputed.ld.xpath_search("//NewsArticle/articleSection", scalar=True)
            if section:
                return generic_topic_parsing([section])
            return []

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                author_selector=re.compile(r"\(foto (?P<credits>.*)\)\s*$"),
            )
