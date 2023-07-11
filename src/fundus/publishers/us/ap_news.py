import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class APNewsParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2023, 7, 10)
        _author_selector: XPath = XPath(f"{CSSSelector('div.CardHeadline').path}/span/span[1]")
        _paragraph_selector = XPath("//div[@data-key = 'article']/p")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            # AP News does not have all the article's authors listed in the linked data.
            # Therefore, we try to parse the article's authors from the document.
            try:
                # Example: "By AUTHOR1, AUTHOR2 and AUTHOR3"
                author_string: str = self._author_selector(self.precomputed.doc)[0].text_content()
                author_string = author_string[3:]  # Strip "By "
            except IndexError:
                # Fallback to the generic author parsing from the linked data.
                return generic_author_parsing(self.precomputed.ld.get_value_by_key_path(["NewsArticle", "author"]))

            return re.split(r"\sand\s|,\s", author_string)

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.get_value_by_key_path(["NewsArticle", "datePublished"]))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.get_value_by_key_path(["NewsArticle", "headline"])

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

    class V1S1(V1):
        VALID_UNTIL = datetime.date.today()
        _author_selector = CSSSelector("div.Page-authors")
        _paragraph_selector = CSSSelector("div.RichTextStoryBody > p")
