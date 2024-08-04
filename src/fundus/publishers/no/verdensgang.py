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


class VerdensGangParser(ParserProxy):
    class V1(BaseParser):

        _paragraph_selector = CSSSelector("article > section.article-body > p")
        _sub_headline_selector = CSSSelector("article > header > p")
        _paywall_selector = CSSSelector("#paywall-login-link")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._sub_headline_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("article:author"))

        @attribute
        def topics(self) -> List[str]:
            filtered_topics = []
            for topic, metatag in self.precomputed.meta.items():
                if "article:tag" in topic:
                    filtered_topics.append(metatag)
            return generic_topic_parsing(filtered_topics)

        @attribute
        def free_access(self) -> bool:
            return not self._paywall_selector(self.precomputed.doc)
