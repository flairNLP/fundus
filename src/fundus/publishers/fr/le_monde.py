import datetime
import re
from dataclasses import replace
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

        # entries answering reader comments are no content of the ticker itself, so nothing of them is selected.
        # Their boundary is kept though, otherwise their dates and images would end up in the preceding entry
        _entry = "//section[@data-post-id][not(.//div[contains(@class, 'post__live-container--comment-content')])]"
        _live_ticker = LiveTickerSelectors(
            # every entry is a `section` carrying a `data-post-id`, which the sponsored slots and the key facts lack
            boundary_selector=XPath("//section[contains(@class, 'post__live-container') and @data-post-id]"),
            # the "read also" teasers and embeds inside of entries are no content of the entry either
            paragraph_selector=XPath(
                f"{_entry}//p[contains(@class, 'post__live-container--answer-text')] | "
                f"{_entry}//blockquote[contains(@class, 'post__live-container--citation')]/p | "
                f"{_entry}//ul[contains(@class, 'article__unordered-list')]/li"
            ),
            summary_selector=_summary_selector,
            subheadline_selector=XPath(f"{_entry}//h2[contains(@class, 'post__live-container--title')]"),
            # "16:12" or "Le 27/09 à 22:01"
            date_selector=XPath(f"{_entry}//span[@class='date']"),
            date_dayfirst=True,
            date_tz=ZoneInfo("Europe/Paris"),
            author_selector=XPath(f"{_entry}//span[contains(@class, 'post__live-container--answer-author')]"),
            image_selector=XPath(f"{_entry}//img[contains(@class, 'post__live-container--img')]"),
            image_caption_selector=XPath("./ancestor::figure//figcaption/text()[normalize-space()][1]"),
        )

        @attribute
        def body(self) -> Optional[Union[ArticleBody, LiveTickerBody]]:
            return extract_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                tag_filter=self._kicker_filter,
                # entries of the current day only state their time, older ones day and month, so the rest is taken
                # from the ticker's last update
                live_ticker=replace(self._live_ticker, date_default=self._live_ticker_last_update()),
            )

        def _live_ticker_last_update(self) -> Optional[datetime.datetime]:
            meta = self.precomputed.meta
            if not (update := generic_date_parsing(meta.get("dateModified") or meta.get("og:article:published_time"))):
                return None
            # entries are written in local time; seconds would otherwise be filled in from the update
            return update.astimezone(ZoneInfo("Europe/Paris")).replace(second=0, microsecond=0)

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
                live_ticker=self._live_ticker,
                image_selector=XPath("//figure/descendant::img[1]"),
                caption_selector=XPath("./ancestor::figure//figcaption/text()"),
                author_selector=XPath("./ancestor::figure//figcaption/span"),
            )
