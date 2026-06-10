import datetime
from typing import List, Optional

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


class GlobalNewsParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            "//article/ul/li | //article/p[not(text()='—') and text() and not(re:test(string(), 'This report by .* was first published'))]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _subheadline_selector = XPath("//article/*[self::h3 or (self::p and strong and not(text()))]")

        _bloat_topics = {"Canada"}

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"), result_filter=self._bloat_topics)

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                caption_selector=XPath("./ancestor::figure//figcaption/span"),
                author_selector=XPath("./ancestor::figure//figcaption/cite"),
            )
