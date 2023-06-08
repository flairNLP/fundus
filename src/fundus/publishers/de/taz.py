import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_id_url_parsing,
    generic_topic_parsing,
)


class TazParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector(".sectbody > p[class*='article']")
        _summary_selector = CSSSelector(".intro")
        _subheadline_selector = CSSSelector(".sectbody > h6")
        _url_id_pattern = "(?:taz.de/)(?:.*)!([0-9]{7})"

        @attribute(validate=False)
        def id(self) -> Optional[str]:
            return generic_id_url_parsing(self.precomputed.meta.get("og:url"), self._url_id_pattern)

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("taz:title")

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))
