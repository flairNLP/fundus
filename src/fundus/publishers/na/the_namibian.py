from datetime import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
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
            # publishing date wird is given in YYYY-mm-ddTHH:MM:SS+HH:MM since %:z in datetime was only intruduced in python 3.12, it needs to be handled by splitting the string
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def title(self) -> Optional[str]:
            title = self.precomputed.meta.get("og:title")
            # Verfication Necessary if title is non None, to prevent error on function call
            if not not title:
                title = title.removesuffix(" - The Namibian")
            return title

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.get_value_by_key_path(["Person", "name"]))

        @attribute(validate=False)
        def language(self) -> Optional[str]:
            # Since The Namibian publishes articles in English and Oshiwambo, I added the attribute as well.
            return self.precomputed.meta.get("og:locale")
