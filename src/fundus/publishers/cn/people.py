import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_date_parsing,
    generic_topic_parsing,
    parse_title_from_root,
)


class PeopleParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("div.rm_txt_con > p")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(self.precomputed.doc, paragraph_selector=self._paragraph_selector)

        @attribute
        def title(self) -> Optional[str]:
            return parse_title_from_root(self.precomputed.doc)

        @attribute
        def authors(self) -> List[str]:
            _selector = CSSSelector("div.edit")
            authors = [name.strip("()") for name in _selector(self.precomputed.doc)[0].text_content().split("、")]
            if authors[0].find("：") != -1:
                authors[0] = authors[0][authors[0].find("：") + 1 :]
            return authors

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("publishdate"))

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"), delimiter=" ")
