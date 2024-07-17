import datetime
import re
from typing import List, Optional, Pattern

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    apply_substitution_pattern_over_list,
    extract_article_body_with_selector,
    generic_date_parsing,
    generic_topic_parsing,
)


class BSZParser(ParserProxy):
    class V1(BaseParser):
        _author_substitution_pattern: Pattern[str] = re.compile(r"FUNKE Mediengruppe")
        _paragraph_selector = XPath(
            "//div[@class='article-body']//p[not(not(text()) or @rel='author' or em[@class='print'] or contains(@class, 'font-sans'))]"
        )
        _summary_selector = XPath("//div[@class='article-body']//p[contains(@class, 'font-sans')]")
        _subheadline_selector = XPath(
            "//div[@class='article-body']//h3[not("
            "contains(text(), 'Alle Artikel der Serie')"
            " or contains(text(), 'Mehr zum Thema')"
            " or contains(text(), 'weitere Videos')"
            " or contains(text(), 'Auch interessant')"
            " or contains(text(), 'Weitere News'))]"
        )
        _topics_selector = XPath("//div[@class='not-prose  mb-4 mx-5 font-sans']/ul/li")

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
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            if topics := generic_topic_parsing(self.precomputed.meta.get("news_keywords")):
                return topics
            else:
                pass
            return [
                re.sub(r"\s*–.+", "", node.text_content()).strip()
                for node in self._topics_selector(self.precomputed.doc)
            ]

        @attribute
        def authors(self) -> List[str]:
            authors = []
            for author in self.precomputed.ld.bf_search("author", default=[]):
                name_string = author.get("name")
                authors.extend(re.split(r"und|,", name_string))
            return apply_substitution_pattern_over_list(
                [author.strip() for author in authors], self._author_substitution_pattern
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))
