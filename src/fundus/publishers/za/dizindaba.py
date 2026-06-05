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


class DizindabaParser(ParserProxy):
    class V1(BaseParser):
        _author_selector = r"(?i)(intatheli|by):(?P<author>[A-z\s]*)\|"
        _compiled_author_selector = re.compile(_author_selector)

        _paragraph_selector = XPath(
            f"//div[@itemprop='articleBody']/p[not(re:test(string(),'{_author_selector}')) and text()]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _subheadline_selector = XPath("//div[@itemprop='articleBody']/p[not(position()>1 or text())]/strong")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            author_candidate = self.precomputed.doc.xpath("//div[@itemprop='articleBody']/p[1]/text()")
            if author_candidate and (match := self._compiled_author_selector.search(author_candidate[0])):
                return generic_author_parsing(match.group("author"))
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//article"),
            )
