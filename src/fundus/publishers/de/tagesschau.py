import datetime
import re
from typing import List, Optional, Union

from lxml.cssselect import CSSSelector
from lxml.etree import XPath
from zoneinfo import ZoneInfo

from fundus.parser import (
    ArticleBody,
    BaseParser,
    Image,
    LiveTickerBody,
    ParserProxy,
    attribute,
)
from fundus.parser.utility import (
    LiveTickerSelectors,
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

        _image_selector = XPath(
            "//*[not(self::div and @class='teaser-absatz__image')]/div[@class='ts-picture__wrapper']//img"
            "|//div[contains(@class, 'article-head__media')]/div[@class='ts-picture__poster-wrapper']//img"
        )
        _image_caption_selector = XPath("./ancestor::div[contains(@class, 'absatzbild ')]")
        _image_alt_selector = XPath("./@title")
        _image_author_selector = re.compile(r"\|(?P<credits>.+)")

        _live_ticker = LiveTickerSelectors(
            boundary_selector=XPath("//div[contains(@class, 'liveblog--anchor')]"),
            paragraph_selector=XPath("//p[contains(@class,'textabsatz ') and not(strong)]"),
            summary_selector=XPath("//article//p[@class='article-head__shorttext']|//article/div/ul/li[not(@class)]"),
            subheadline_selector=XPath("//h2[@class='meldung__subhead']"),
            date_selector=XPath("//div[@class='liveblog__datetime']"),
            date_dayfirst=True,
            date_tz=ZoneInfo("Europe/Berlin"),
            image_selector=XPath("//div[contains(@class, 'absatzbild ')]//div[@class='ts-picture__wrapper']//img"),
            image_caption_selector=_image_caption_selector,
            image_alt_selector=_image_alt_selector,
            image_author_selector=_image_author_selector,
        )

        @attribute
        def body(self) -> Optional[Union[ArticleBody, LiveTickerBody]]:
            return extract_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
                live_ticker=self._live_ticker,
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
                live_ticker=self._live_ticker,
            )
