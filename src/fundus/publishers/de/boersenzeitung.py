import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class BoersenZeitungParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("p")
        _subheadline_selector = CSSSelector("h2.no-tts no-tts wp-block-ppi-subheading")
        _topic_selector = CSSSelector("a[href^='/thema'] > span")
        _paywall_selector = CSSSelector("storefront-html.paywall-headline > div")

        @attribute
        def title(self) -> Optional[str]:
            fulltitle = self.precomputed.meta.get("og:title")
            assert isinstance(fulltitle, str) #had to add this for mypy
            title = str(fulltitle.split("|")[0].strip())
            return title

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("twitter:misc:Written by"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published:time"))

        @attribute
        def topics(self) -> List[str]:
            return [node.text_content().strip() for node in self._topic_selector(self.precomputed.doc)]

        @attribute
        def free_access(self) -> bool:
            # print(self._paywall_selector(self.precomputed.doc).text_content().strip())
            return not [node.text_content().strip() for node in self._paywall_selector(self.precomputed.doc)]
