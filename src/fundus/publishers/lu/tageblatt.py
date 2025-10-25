import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    image_extraction,
)


class TageblattParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[@class='text-content']/p[@class='text' and normalize-space(text())]")
        _summary_selector = XPath("//p[contains(@class,'teaser__text')]")
        _subheadline_selector = XPath("//div[@class='text-content']//h2[contains(@class,'crosshead')]")

        _bloat_authors = ["No Author", "Redaktion"]

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return [
                author
                for author in generic_author_parsing(self.precomputed.ld.bf_search("author"))
                if author not in self._bloat_authors
            ]

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=CSSSelector("h1"),
                author_selector=re.compile(r"(?i)(Foto|Bild):\s*(?P<credits>.*)"),
            )
