import re
from datetime import datetime
from typing import List, Optional, Pattern

import lxml.html
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.data import Image
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_nodes_to_text,
    generic_topic_parsing,
    image_extraction,
)


class KommersantParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath("//header/h2")
        _paragraph_selector = XPath(
            "//div[contains(@class, 'article_text_wrapper')]/p[not(contains(@class, 'document_authors') or (not(text()) and b))]"
        )

        _author_selector = XPath("//p[@class='doc__text document_authors']")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(generic_nodes_to_text(self._author_selector(self.precomputed.doc)))

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//header/h1"),
                image_selector=XPath("//figure//img[not(contains(@class, 'fallback'))]"),
                caption_selector=XPath("./ancestor::figure//figcaption/p"),
                author_selector=re.compile(r"(?i)Фото:(?P<credits>.+)"),
            )
