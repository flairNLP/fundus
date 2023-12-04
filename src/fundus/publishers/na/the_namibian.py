from datetime import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class TheNamibianParser(ParserProxy):
    class V1(BaseParser):
        selector = CSSSelector("p")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self.selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def title(self) -> Optional[str]:
            title = self.precomputed.meta.get("og:title")
            # Verfication necessary if title is None, to prevent error on function call
            if not not title:
                if " - The Namibian" in title:
                    title = title.split(" - The Nam")[0]
            return title

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.get_value_by_key_path(["Person", "name"]))
