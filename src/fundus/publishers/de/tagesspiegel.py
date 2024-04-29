from fundus.parser import ParserProxy, BaseParser, attribute
from typing import Optional
from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import extract_article_body_with_selector, generic_author_parsing, generic_date_parsing, generic_topic_parsing
import datetime

class TagesspiegelParser(ParserProxy):
    class V1(BaseParser):

        @attribute
        def title(self) -> Optional[str]:
            # Use the `get` function to retrieve data from the `meta` precomputed attribute
            return self.precomputed.meta.get("og:title")
        
        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))
