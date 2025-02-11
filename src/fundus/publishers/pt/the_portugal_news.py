import datetime
import re
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    image_extraction,
)


class ThePortugalNewsParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[@class='article-body']//p[string-length(text())>1]")
        _subheadline_selector = XPath("//div[@class='article-body']/p/b[not(u)]")
        _summary_selector = XPath("//div[@class='fs-4 font-semibold mb-3']")

        _author_selector = XPath("//div[@class='col-lg-10 order-lg-1']/p//text()")

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
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def authors(self) -> List[str]:
            author_objects = self._author_selector(self.precomputed.doc)
            if author_objects and (author := re.search(r"(?i)by\s*(?P<authors>.*),[\r\sr\n]*in", author_objects[0])):
                return generic_author_parsing(author.group("authors"))
            return []

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                author_selector=re.compile(r"(?i)credits:\s*(?P<credits>.*)"),
            )
