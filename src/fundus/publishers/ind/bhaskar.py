import datetime
import re
from typing import List, Optional, Pattern

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class BhaskarParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//article //p | //article //*[@style='border-bottom:none'] //li")

        _topic_bloat_pattern: Pattern[str] = re.compile(r"news", flags=re.IGNORECASE)

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return [
                topic
                for topic in generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))
                if not re.search(self._topic_bloat_pattern, topic)
            ]
