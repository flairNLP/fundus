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
    image_extraction,
)


class TheNamibianParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime(year=2024, month=1, day=31).date()
        _summary_selector = XPath("//div[contains(@class, 'tdb-block-inner')]/p[position()=1]")
        _paragraph_selector = XPath("//div[contains(@class, 'tdb-block-inner')]/p[position()>1]")

        _title_substitution_pattern: Pattern[str] = re.compile(r" - The Namibian$")
        _author_selector = XPath("//Person/name")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def title(self) -> Optional[str]:
            title = self.precomputed.meta.get("og:title")
            if title is not None:
                return re.sub(self._title_substitution_pattern, "", title)
            return title

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.xpath_search(self._author_selector))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//h1[@class='tdb-title-text']"),
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.today().date()
        _paragraph_selector = XPath("//div[contains(@class, 'entry-content')]/p[(text() or strong) and position()>1]")
        _summary_selector = XPath("//div[contains(@class, 'entry-content')]/p[(text() or strong) and position()=1] ")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            html = re.sub(r"(<br>)+", "<p>", self.precomputed.html)
            doc = lxml.html.document_fromstring(html)
            return extract_article_body_with_selector(
                doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//main"),
            )
