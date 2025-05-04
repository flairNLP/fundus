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


class WochenblattParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[@class='entry-content']/p[position() < last() and not(b)]")
        _subheadline_selector = XPath(
            "//div[@class='entry-content']/*[(self::p or self::h3) and position() < last() and b]"
        )

        _author_selector = XPath("//div[@class='entry-content']/p[last()]")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute(priority=1)
        def authors(self) -> List[str]:
            # The author is only listed in the last line of the article
            authors = self._author_selector(self.precomputed.doc)
            if authors:
                author = authors[0].text_content().strip()
                if match := re.match(r"(?i)^wochenblatt\s*/\s*(?P<authors>([\w ]+))", author):
                    return generic_author_parsing(match.group("authors"))
            return []

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return re.sub(r"(?i)\s*-\s*wochenblatt", "", self.precomputed.meta.get("og:title") or "")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//div[@class='entry-content']//img"),
            )
