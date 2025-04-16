import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute, function
from fundus.parser.data import ArticleSection, Image, TextSequence
from fundus.parser.utility import (
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
    parse_json,
)


class WestAustralianParser(ParserProxy):
    class V1(BaseParser):
        _page_data_selector = XPath(
            "string(//script[re:test(text(), 'window.PAGE_DATA')])",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )

        @function(priority=1)
        def _parse_page_content(self):
            if not (parsed_json := parse_json(self._page_data_selector(self.precomputed.doc))):
                raise ValueError("Couldn't parse page data")
            self.precomputed.ld.add_ld(parsed_json, "windows.PAGE_DATA")

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

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=CSSSelector("div#ArticleContent > p"),
                upper_boundary_selector=CSSSelector("article"),
                lower_boundary_selector=CSSSelector("div#footer"),
                caption_selector=XPath("./ancestor::figure //span[contains(@class, 'CaptionText')] /span[1]"),
                author_selector=XPath("./ancestor::figure //span[contains(@class, 'CaptionText')] /span[last()]"),
            )
