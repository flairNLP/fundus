import datetime
import re
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


class MalayMailParser(ParserProxy):
    class V1(BaseParser):
        # Use negated _subheadline_selector as _paragraph_selector to ensure no double parsing
        _paragraph_selector = XPath("//div[@class='article-body']/p[text() or not(b)]")
        _subheadline_selector = XPath("//div[@class='article-body']/p[not(text()) and b]")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//div[contains(@class, 'image')]//img"),
                caption_selector=XPath("(./ancestor::div[contains(@class, 'image')])[1]//div[@class='image-caption']"),
                author_selector=re.compile(r"\s*—\s*(?P<credits>.*)$"),
            )
