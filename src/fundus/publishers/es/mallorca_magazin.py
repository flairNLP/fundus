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


class MallorcaMagazinParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[@id='post-text']//p")
        _subheadline_selector = XPath("//div[@id='post-text']//*[(self::h4 or self::h2) and not(@class)]")
        _summary_selector = XPath("//h2[@class='post-subtitle']")

        _topic_selector = XPath("//div[@class='post-tags']//li")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def topics(self) -> List[str]:
            return [node.text_content().strip() for node in self._topic_selector(self.precomputed.doc)]

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                image_selector=XPath("//figure//img|//div[@id='post-text']//p/img"),
                paragraph_selector=self._paragraph_selector,
                caption_selector=XPath(
                    "./ancestor::div[@class='col-sm-12']//p[@class='img-description'] | "
                    "./ancestor::figure//figcaption"
                ),
                author_selector=re.compile(r"\|(?P<credits>.+)"),
            )
