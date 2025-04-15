import re
from datetime import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import (
    ArticleBody,
    BaseParser,
    Image,
    ParserProxy,
    attribute,
    utility,
)
from fundus.parser.utility import image_extraction


class DailyNewsTZParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("div.cs-entry__subtitle")
        _subheadline_selector = XPath("//div[@class='entry-content']//p[not(text() or position()=1)]//span//strong")
        _paragraph_selector = XPath(
            "//div[@class='entry-content']"
            "//p[not(re:test(string(.), '^(SOMA|ALSO READ):') or span)] | "
            "//div[@class='entry-content']//p[not(position()=1)]//span[not(span) and text()] |"
            "//div[@class='entry-content']//p//span/span[text()] | "
            "//div[@class='entry-content']//p[position()=1]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )

        @attribute
        def title(self) -> Optional[str]:
            return re.sub(r"(?i)\s*-\s*(daily\s*news|habari\s*leo)\s*", "", self.precomputed.meta.get("og:title") or "")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            article_body = utility.extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )
            return article_body

        @attribute
        def authors(self) -> List[str]:
            return utility.generic_author_parsing(self.precomputed.meta.get("twitter:data1"))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return utility.generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//figure//img[1]|//div[@id='content']//p/img"),
                caption_selector=XPath(
                    "./ancestor::figure//figcaption | "
                    "./ancestor::div[@class='cs-entry__thumbnail']//div[@class='cs-entry__thumbnail-caption']"
                ),
            )
