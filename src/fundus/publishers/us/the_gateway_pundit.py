from datetime import datetime
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class TheGatewayPunditParser(ParserProxy):
    class V1(BaseParser):
        _related = r"^Click\s$"
        _paragraph_selector = XPath(
            f"(//div[@class='entry-content'] | //div[@class='entry-content']/blockquote[not(@class='twitter-tweet')]) "
            f"/p[not(child::img or child::script or re:test(text(), '{_related}')) and text()]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.get_value_by_key_path(["Article", "author"]))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def title(self) -> Optional[str]:
            if (title := self.precomputed.meta.get("og:title")) is not None:
                title = title.split("|")[0].strip()
            return title
