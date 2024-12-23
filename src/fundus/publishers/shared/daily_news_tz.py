import re
from datetime import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute, utility


class DailyNewsTZParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("div.cs-entry__subtitle")
        _subheadline_selector = XPath("//div[@class='entry-content']//p[not(text() or position()=1)]//span//strong")
        _paragraph_selector = XPath("//div[@class='entry-content']//p[text() or position()=1]")

        @attribute
        def title(self) -> Optional[str]:
            return re.sub(r"(?i)\s*-\s*(daily\s*news|habari\s*leo)\s*", "", self.precomputed.meta.get("og:title"))

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
