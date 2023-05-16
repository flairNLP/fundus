from datetime import datetime
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class ReutersParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//p[starts-with(@data-testid, 'paragraph') and position() > 1]")
        _summary_selector = XPath("//p[starts-with(@data-testid, 'paragraph')][1]")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            # Reuters also has authors listed in the ld+json.
            # But there, the author names are listed at "byline" instead of "name".
            # This is not supported by the generic author parsing.
            return generic_author_parsing(self.precomputed.meta.get("article:author"))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.ld.get_value_by_key_path(["NewsArticle", "datePublished"]))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.get_value_by_key_path(["NewsArticle", "headline"])

        @attribute
        def topics(self) -> List[str]:
            # Reuters does not have very meaningful topics in the "keywords" meta.
            # Example: ['BLR', 'EGS', 'SOC', 'SOCC', 'SPO', ...]
            # But interesting topics from the meta may be found in these fields:
            #   - article:section                       ("Aerospace & Defense")
            #   - analyticsAttributes.topicChannel      ("Business")
            #   - analyticsAttributes.topicSubChannel   ("Aerospace & Defense")
            #   - DCSext.ChannelList                    ("Business;Asia Pacific;World")
            topics: list[Optional[str]] = [
                self.precomputed.meta.get("article:section"),
                self.precomputed.meta.get("analyticsAttributes.topicChannel"),
                self.precomputed.meta.get("analyticsAttributes.topicSubChannel"),
            ]
            topics.extend(generic_topic_parsing(self.precomputed.meta.get("DCSext.ChannelList"), delimiter=";"))

            # Remove empty topics and duplicates deterministically
            processed_topics: list[str] = list(dict.fromkeys(topic for topic in topics if topics not in [None, ""]))
            return processed_topics
