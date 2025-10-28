import datetime
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
    generic_topic_parsing,
    image_extraction,
)


class SZParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.datetime(2024, 2, 1).date()
        _paragraph_selector: XPath = CSSSelector("main [itemprop='articleBody'] > p, main .css-korpch > div > ul > li")
        _summary_selector: XPath = CSSSelector("main [data-manual='teaserText']")
        _subheadline_selector: XPath = CSSSelector("main [itemprop='articleBody'] > h3")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                caption_selector=XPath("./ancestor::figure//figcaption/text()"),
                author_selector=XPath("./ancestor::figure//figcaption/small"),
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()
        _paragraph_selector = XPath(
            "//div[@itemprop='articleBody'] //p[@data-manual='paragraph' and not(contains(text(), '© dpa-infocom'))]"
        )
        _summary_selector = CSSSelector("main [data-manual='teaserText']")
        _subheadline_selector = XPath(
            "//div[@itemprop='articleBody']//h3[@data-manual='subheadline'] |"
            "//div[@itemprop='articleBody']//h2[@data-manual='subheadline']"
        )

        _live_ticker_boundary_selector = XPath("//div[contains(@class, 'event__body')]")
        _live_ticker_paragraph_selector = XPath(
            "//article//div[contains(@class, 'event__body')]//li|//article//div[contains(@class, 'event__body')]//div[@class='tik4-rich-text tik4-rich-text--de']/div"
        )
        _live_ticker_subheadline_selector = XPath(
            "//article//div[contains(@class, 'event__body')]//h2|//article//div[contains(@class, 'event__body')]//h3"
        )
        _live_ticker_date_selector = XPath("//article//div[contains(@class, 'event__body')]//time")
        _live_ticker_author_selector = XPath(
            "//article//div[contains(@class, 'event__body')]//div[@class='tik4-author__name']"
        )
        _live_ticker_summary_selector = XPath("//p[@data-manual='teaserText']")

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
                    self.precomputed.doc,
                    summary_selector=self._live_ticker_summary_selector,
                    subheadline_selector=self._live_ticker_subheadline_selector,
                    paragraph_selector=self._live_ticker_paragraph_selector,
                    entry_boundary_selector=self._live_ticker_boundary_selector,
                    author_selector=self._live_ticker_author_selector,
                    date_selector=self._live_ticker_date_selector,
                )
