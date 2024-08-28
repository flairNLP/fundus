import datetime
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
from fundus.scraping.filter import regex_filter


class NationalPostParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("article p.article-subtitle")
        _subheadline_selector = XPath(
            "//section[@class='article-content__content-group article-content__content-group--story']/p/strong | "
            "//section[@class='article-content__content-group article-content__content-group--story']/h3"
        )
        _paragraph_selector = XPath(
            "//section[@class='article-content__content-group article-content__content-group--story']/p[text()]"
        )

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
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            preliminary_topics = self.precomputed.ld.bf_search("keywords")
            filter_list = ["Curated", "News", "Newsroom daily", "story", "Canada", "World"]
            topic_filter = regex_filter(
                r"([0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}|NLP Entity Tokens|NLP Category|NP Comment)"
            )
            filtered_topics = [
                topic for topic in preliminary_topics if not topic_filter(topic) and topic not in filter_list
            ]
            return generic_topic_parsing(filtered_topics)
