import datetime
import re
from typing import List, Optional, Union

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.data import LiveTickerBody
from fundus.parser.utility import (
    extract_article_body_with_selector,
    extract_live_ticker_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    image_extraction,
)


class TagesschauParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//article/p[position() > 1]")
        _summary_selector = XPath("//article/p[1]")
        _subheadline_selector = XPath("//article/h2")
        _author_selector = XPath('string(//div[contains(@class, "authorline__author")])')
        _topic_selector = CSSSelector("div.meldungsfooter .taglist a")

        _live_ticker_boundary_selector = XPath("//div[contains(@class, 'liveblog--anchor')]")
        _live_ticker_paragraph_selector = XPath("//p[contains(@class,'textabsatz ') and not(strong)]")
        _live_ticker_subheadline_selector = XPath("//h2[@class='meldung__subhead']")
        _live_ticker_date_selector = XPath("//div[@class='liveblog__datetime']")
        _live_ticker_summary_selector = XPath("//article/p[strong]|//article/div/ul/li[not(@class)]")

        @attribute
        def body(self) -> Optional[Union[ArticleBody, LiveTickerBody]]:
            if not self._live_ticker_boundary_selector(self.precomputed.doc):
                return extract_article_body_with_selector(
                    self.precomputed.doc,
                    summary_selector=self._summary_selector,
                    subheadline_selector=self._subheadline_selector,
                    paragraph_selector=self._paragraph_selector,
                )
            else:
                return extract_live_ticker_body_with_selector(
                    doc=self.precomputed.doc,
                    entry_boundary_selector=self._live_ticker_boundary_selector,
                    summary_selector=self._live_ticker_summary_selector,
                    paragraph_selector=self._live_ticker_paragraph_selector,
                    subheadline_selector=self._live_ticker_subheadline_selector,
                    date_selector=self._live_ticker_date_selector,
                )

        @attribute
        def authors(self) -> List[str]:
            if raw_author_string := self._author_selector(self.precomputed.doc):
                cleaned_author_string = re.sub(r"^Von |, ARD[^\s,]*", "", raw_author_string)
                return generic_author_parsing(cleaned_author_string)
            else:
                return []

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            topic_nodes = self._topic_selector(self.precomputed.doc)
            return [node.text_content() for node in topic_nodes]

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath(
                    "//*[not(self::div and @class='teaser-absatz__image')]/div[@class='ts-picture__wrapper']//img"
                ),
                alt_selector=XPath("./@title"),
                author_selector=re.compile(r"\|(?P<credits>.+)"),
                caption_selector=XPath("./ancestor::div[contains(@class, 'absatzbild ')]"),
                lower_boundary_selector=self._topic_selector,
            )
