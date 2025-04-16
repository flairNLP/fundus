import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.data import Image
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class NettavisenParser(ParserProxy):
    class V1(BaseParser):
        _bloat_pattern: str = "Les også:"

        _summary_selector = CSSSelector("p.lead-text")
        _subheadline_selector = CSSSelector("div.article-body > h2")
        _paragraph_selector = XPath(
            f"//div[contains(@class,'article-body')] /p[not(re:test(string(), '{_bloat_pattern}'))]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("article:author"))

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("article:tag"))

        @attribute
        def images(self) -> List[Image]:
            author_pattern = r"(Foto:\s*).*$"
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//brick-image-v3 | //img"),
                caption_selector=XPath("./ancestor::div[contains(@class, 'image')]//span[1]"),
                author_selector=XPath(
                    f"re:match(./ancestor::div[contains(@class, 'image')]//span[2], '{author_pattern}')",
                    namespaces={"re": "http://exslt.org/regular-expressions"},
                ),
            )
