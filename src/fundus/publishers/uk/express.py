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
)


class ExpressParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("article > header > h3")
        # only relevant for live-tickers
        _subheadline_selector = CSSSelector("div.live-events h3")
        _paragraph_selector = CSSSelector(
            "article div.text-description:not(.dont-miss) > p, div.live-events div.live-events__entry-text > p"
        )

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("author"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("article:tag"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=CSSSelector("div[role=main] article"),
                image_selector=CSSSelector("div.photo img"),
                caption_selector=XPath("./ancestor::div[contains(@class, 'photo')]/span[@class='newsCaption']/text()"),
                author_selector=XPath(
                    "./ancestor::div[contains(@class, 'photo')]/span[@class='newsCaption']/span[@class='caption']"
                ),
                size_pattern=re.compile(r"/(?P<width>[0-9]+)x(?P<height>[0-9]+)?/"),
            )
