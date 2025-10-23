import datetime
from typing import List, Optional

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.data import ArticleSection, TextSequence
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    normalize_whitespace,
)
from lxml.cssselect import CSSSelector


class StuttgarterZeitungParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("div.article-body p")
        _subheadline_selector = CSSSelector("div.article-body h2")

        @attribute
        def body(self) -> ArticleBody:
            summary_text = self.precomputed.ld.bf_search("description")
            summary = TextSequence([summary_text]) if summary_text else TextSequence([])
                    
            paragraph_elements = self._paragraph_selector(self.precomputed.doc)
            paragraph_texts = [normalize_whitespace(elem.text_content()) for elem in paragraph_elements]

            subheadline_elements = self._subheadline_selector(self.precomputed.doc)

            sections = [ArticleSection(headline=TextSequence([]), paragraphs=TextSequence(paragraph_texts))]

            return ArticleBody(summary=summary, sections=sections)

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))
