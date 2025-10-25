import re
from datetime import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath, tostring
from lxml.html import document_fromstring

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
    transform_breaks_to_paragraphs,
)


class IlGiornaleParser(ParserProxy):
    class V1(BaseParser):
        # Selectors for article body parts
        _paragraph_selector = XPath(
            "//div[contains(@class, 'typography--content')]//p[text() or strong or em] | //div[@class='banner banner--spaced-block banner-evo' and (text() or em or strong)]"
        )
        _subheadline_selector = CSSSelector("div.typography--content h2:not([class])")
        _summary_selector = CSSSelector("p.article__abstract, div.article__abstract")
        _image_selector = XPath(
            "//div[contains(@class, 'article__media')]//img | //section[contains(@class, 'article__content')]//img"
        )

        @attribute
        def title(self) -> Optional[str]:
            # First try JSON-LD
            title = self.precomputed.ld.xpath_search("//NewsArticle/headline", scalar=True)
            if title:
                return str(title)
            # Fallback to meta tags
            return self.precomputed.meta.get("og:title")

        @attribute
        def authors(self) -> List[str]:
            # Extract authors from schema.org NewsArticle data
            authors = self.precomputed.ld.xpath_search("//NewsArticle/author")
            if authors:
                return generic_author_parsing(authors)
            return []

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            # Try JSON-LD first
            date_str = self.precomputed.ld.xpath_search("//NewsArticle/datePublished", scalar=True)
            if not date_str:
                # Fallback to meta tags
                date_str = self.precomputed.meta.get("article:published_time")
            return generic_date_parsing(date_str)

        @attribute
        def body(self) -> Optional[ArticleBody]:
            # Clean up HTML by removing ads and handling em/strong/cite tags
            html_string = tostring(self.precomputed.doc).decode("utf-8")
            html_string = re.sub(r"</?(em|strong|cite)>", "", html_string)
            html_string = re.sub(r"<!-- EVOLUTION ADV -->", "", html_string)
            doc = document_fromstring(html_string)

            # Transform br tags to paragraphs for better structure
            doc = transform_breaks_to_paragraphs(doc)

            # Extract article body using utility function
            return extract_article_body_with_selector(
                doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def topics(self) -> List[str]:
            # Try to get topics from keywords
            keywords = self.precomputed.ld.bf_search("keywords")
            if keywords:
                return generic_topic_parsing(keywords)

            # Fallback to articleSection
            section = self.precomputed.ld.xpath_search("//NewsArticle/articleSection", scalar=True)
            if section:
                return generic_topic_parsing([section])

            return []

        @attribute
        def images(self) -> List[Image]:
            # Extract images using the utility function
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=self._image_selector,
                caption_selector=XPath(".//figcaption/text()"),
            )
