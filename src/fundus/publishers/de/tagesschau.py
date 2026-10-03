import datetime
import re
from typing import List, Optional, Union

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import (
    ArticleBody,
    BaseParser,
    Image,
    LiveTickerBody,
    ParserProxy,
    attribute,
)
from fundus.parser.utility import (
    extract_body_with_selector,
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
        _live_ticker_image_selector = XPath(
            "//div[contains(@class, 'absatzbild ')]//div[@class='ts-picture__wrapper']//img"
        )
        _live_ticker_summary_selector = XPath(
            "//article//p[@class='article-head__shorttext']|//article/div/ul/li[not(@class)]"
        )

        _image_selector = XPath(
            "//*[not(self::div and @class='teaser-absatz__image')]/div[@class='ts-picture__wrapper']//img"
        )
        _image_caption_selector = XPath("./ancestor::div[contains(@class, 'absatzbild ')]")
        _image_alt_selector = XPath("./@title")
        _image_author_selector = re.compile(r"\|(?P<credits>.+)")

        @staticmethod
        def _parse_live_ticker_date(date_string: str) -> Optional[datetime.datetime]:
            # dates are given as DD.MM.YYYY, which generic_date_parsing would read month first
            return generic_date_parsing(re.sub(r"(\d{1,2})\.(\d{1,2})\.(\d{4})", r"\3-\2-\1", date_string))

        @attribute
        def body(self) -> Optional[Union[ArticleBody, LiveTickerBody]]:
            return extract_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
                live_ticker_boundary_selector=self._live_ticker_boundary_selector,
                live_ticker_summary_selector=self._live_ticker_summary_selector,
                live_ticker_paragraph_selector=self._live_ticker_paragraph_selector,
                live_ticker_subheadline_selector=self._live_ticker_subheadline_selector,
                live_ticker_date_selector=self._live_ticker_date_selector,
                live_ticker_date_parser=self._parse_live_ticker_date,
                live_ticker_image_selector=self._live_ticker_image_selector,
                live_ticker_image_caption_selector=self._image_caption_selector,
                live_ticker_image_alt_selector=self._image_alt_selector,
                live_ticker_image_author_selector=self._image_author_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            if raw_author_string := self._author_selector(self.precomputed.doc):
                cleaned_author_string = re.sub(r"^Von |, ARD[^\s,]*", "", raw_author_string)
                return generic_author_parsing(cleaned_author_string)
            else:
                return generic_author_parsing(self.precomputed.meta.get("author", ""))

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
                image_selector=self._image_selector,
                alt_selector=self._image_alt_selector,
                author_selector=self._image_author_selector,
                caption_selector=self._image_caption_selector,
                lower_boundary_selector=self._topic_selector,
            )
