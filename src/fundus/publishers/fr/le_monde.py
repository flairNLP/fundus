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
    extract_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    image_extraction,
)


class LeMondeParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            "//p[contains(@class, 'article__paragraph')] | "
            "//section[contains(@class, 'catcher--reference')]//p[contains(@class, 'catcher__desc')]"
        )
        _summary_selector = XPath(
            "//p[contains(@class, 'article__desc') or @id='js-summary-live'] | "
            "//div[@class='ds-description']//span[@class='ds-chapo']"
        )
        _subheadline_selector = XPath(
            "//h2[@class = 'article__sub-title'] | //h3[contains(@class, 'article__chapter-title')]"
        )
        _kicker_filter = XPath("self::span[contains(@class, 'article__kicker')]")

        # every entry is a `section` carrying a `data-post-id`, which the sponsored slots and the key facts lack
        _live_ticker_boundary_selector = XPath("//section[contains(@class, 'post__live-container') and @data-post-id]")
        # entries answering reader comments are no content of the ticker itself, so nothing of them is selected.
        # Their boundary is kept though, otherwise their dates and images would end up in the preceding entry
        _entry = "//section[@data-post-id][not(.//div[contains(@class, 'post__live-container--comment-content')])]"
        # the "read also" teasers and embeds inside of entries are no content of the entry either
        _live_ticker_paragraph_selector = XPath(
            f"{_entry}//p[contains(@class, 'post__live-container--answer-text')] | "
            f"{_entry}//blockquote[contains(@class, 'post__live-container--citation')]/p | "
            f"{_entry}//ul[contains(@class, 'article__unordered-list')]/li"
        )
        _live_ticker_subheadline_selector = XPath(f"{_entry}//h2[contains(@class, 'post__live-container--title')]")
        _live_ticker_author_selector = XPath(f"{_entry}//span[contains(@class, 'post__live-container--answer-author')]")
        # "16:12" or "Le 27/09 à 22:01"
        _live_ticker_date_selector = XPath(f"{_entry}//span[@class='date']")
        _live_ticker_image_selector = XPath(f"{_entry}//img[contains(@class, 'post__live-container--img')]")
        _live_ticker_image_caption_selector = XPath("./ancestor::figure//figcaption/text()[normalize-space()][1]")

        @attribute
        def body(self) -> Optional[Union[ArticleBody, LiveTickerBody]]:
            return extract_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                tag_filter=self._kicker_filter,
                live_ticker_boundary_selector=self._live_ticker_boundary_selector,
                live_ticker_summary_selector=self._summary_selector,
                live_ticker_paragraph_selector=self._live_ticker_paragraph_selector,
                live_ticker_subheadline_selector=self._live_ticker_subheadline_selector,
                live_ticker_date_selector=self._live_ticker_date_selector,
                live_ticker_date_dayfirst=True,
                # entries only state their time, or day and month, so the rest is taken from the ticker's start
                live_ticker_date_default=self._live_ticker_start(),
                live_ticker_author_selector=self._live_ticker_author_selector,
                live_ticker_image_selector=self._live_ticker_image_selector,
                live_ticker_image_caption_selector=self._live_ticker_image_caption_selector,
            )

        def _live_ticker_start(self) -> Optional[datetime.datetime]:
            if not (start := generic_date_parsing(self.precomputed.meta.get("og:article:published_time"))):
                return None
            # entries are written in local time and naive, like the ones of other live tickers
            return start.astimezone(ZoneInfo("Europe/Paris")).replace(tzinfo=None, second=0, microsecond=0)

        @attribute
        def title(self) -> Optional[str]:
            # Use the `get` function to retrieve data from the `meta` precomputed attribute
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return self.precomputed.ld.bf_search("keywords")  # type: ignore

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            # Use the `get` function to retrieve data from the `meta` precomputed attribute
            return generic_date_parsing(self.precomputed.meta.get("og:article:published_time"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(
                self.precomputed.meta.get("og:article:author"),
                split_on=[",", " et "],
                substitution_pattern=re.compile(r"\s*\(service [^)]*\)"),
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=CSSSelector("article"),
                live_ticker_boundary_selector=self._live_ticker_boundary_selector,
                image_selector=XPath("//figure/descendant::img[1]"),
                caption_selector=XPath("./ancestor::figure//figcaption/text()"),
                author_selector=XPath("./ancestor::figure//figcaption/span"),
            )
