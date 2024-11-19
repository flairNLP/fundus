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
    generic_topic_parsing,
    image_extraction,
    parse_title_from_root,
)


class PeopleParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("div.rm_txt_con > p")

        _author_selector = CSSSelector("div.edit")
        _author_pattern = re.compile(r"：(.*)\)")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(self.precomputed.doc, paragraph_selector=self._paragraph_selector)

        @attribute
        def title(self) -> Optional[str]:
            return parse_title_from_root(self.precomputed.doc)

        @attribute
        def authors(self) -> List[str]:
            if (author_nodes := self._author_selector(self.precomputed.doc)) and len(author_nodes) == 1:
                if match := re.search(self._author_pattern, author_nodes.pop().text_content()):
                    return generic_author_parsing(match.group(1), split_on=["、"])
            return []

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("publishdate"))

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"), delimiter=" ")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//img"),
                upper_boundary_selector=XPath("//div[@class='layout route cf']"),
                relative_urls=XPath("string((//head//link[@rel='stylesheet'])[1]/@href)"),
            )
