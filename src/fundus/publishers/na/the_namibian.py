import re
from datetime import datetime
from typing import List, Optional, Pattern

import lxml.html
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute, function
from fundus.parser.base_parser import Precomputed
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    get_ld_content,
    get_meta_content,
)


class TheNamibianParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime(year=2024, month=1, day=31).date()
        _summary_selector = XPath("//div[contains(@class, 'tdb-block-inner')]/p[position()=1]")
        _paragraph_selector = XPath("//div[contains(@class, 'tdb-block-inner')]/p[position()>1]")
        _title_substitution_pattern: Pattern[str] = re.compile(r" - The Namibian$")

        @attribute
        def body(self) -> ArticleBody:
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
            return generic_author_parsing(self.precomputed.ld.get_value_by_key_path(["Person", "name"]))

    class V1_1(V1):
        VALID_UNTIL = datetime.today().date()
        _paragraph_selector = XPath("//div[contains(@class, 'entry-content')]/p[(text() or strong) and position()>1]")
        _summary_selector = XPath("//div[contains(@class, 'entry-content')]/p[(text() or strong) and position()=1]")

        def _base_setup(self, html: str) -> None:
            html = re.sub(r"(<br>)+", "<p>", html)
            doc = lxml.html.document_fromstring(html)
            self.precomputed = Precomputed(html, doc, get_meta_content(doc), get_ld_content(doc))
