import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing, generic_id_url_parsing,
)


class SZParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector('main [itemprop="articleBody"] > p, ' "main .css-korpch > div > ul > li")
        _summary_selector = CSSSelector("main [data-manual='teaserText']")
        _subheadline_selector = CSSSelector("main [itemprop='articleBody'] > h3")
        _url_id_pattern = "(?:sueddeutsche.de/).*(?:1.)([0-9]{7})"

        @attribute
        def body(self) -> ArticleBody:
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
        def id(self) -> Optional[str]:
            return generic_id_url_parsing(self.precomputed.meta.get('og:url'), self._url_id_pattern)

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))
