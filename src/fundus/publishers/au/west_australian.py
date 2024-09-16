import datetime
import json
import re
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute, function
from fundus.parser.data import ArticleSection, TextSequence
from fundus.parser.utility import (
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    sanitize_json,
)


class WestAustralianParser(ParserProxy):
    class V1(BaseParser):
        _page_data_selector = XPath(
            "string(//script[re:test(text(), 'window.PAGE_DATA')])",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _json_type_pattern = re.compile(r"^(?P<type>.*)=\s*{")
        _json_undefined_pattern = re.compile(r'":\s*undefined')

        @function(priority=1)
        def _parse_page_content(self):
            page_data_content = self._page_data_selector(self.precomputed.doc)

            if not page_data_content or not (sanitized := sanitize_json(page_data_content)):
                return

            json_string = re.sub(self._json_undefined_pattern, r'": null', sanitized)

            try:
                json_content = json.loads(json_string)
            except json.JSONDecodeError:
                return

            self.precomputed.ld.add_ld(json_content, "windows.PAGE_DATA")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            content_blocks = self.precomputed.ld.xpath_search(XPath("//publication/content/blocks"))
            paragraphs = []
            for block in content_blocks:
                if block.get("kind") == "text" and (text := block.get("text")):
                    paragraphs.append(text)
            section = ArticleSection(headline=TextSequence([]), paragraphs=TextSequence(paragraphs))
            return ArticleBody(summary=TextSequence([]), sections=[section])

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))
