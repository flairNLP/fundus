from datetime import date, datetime
from typing import List, Optional

import lxml.html
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute, function
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class ReutersParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = date(2024, 1, 1)
        _paragraph_selector = XPath("(//p[starts-with(@data-testid, 'paragraph')])[position() > 1]")
        _summary_selector = XPath("(//p[starts-with(@data-testid, 'paragraph')])[1]")
        _subheadline_selector = XPath("//div[contains(@class, 'article-body')] /h2[@data-testid='Heading']")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            # Reuters also has authors listed in the ld+json.
            # But there, the author names are listed at "byline" instead of "name".
            # This is not supported by the generic author parsing.
            return generic_author_parsing(self.precomputed.meta.get("article:author"))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.ld.xpath_search("NewsArticle/datePublished", scalar=True))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.xpath_search("NewsArticle/headline", scalar=True)

        @attribute
        def topics(self) -> List[str]:
            # Reuters does not have very meaningful topics in the "keywords" meta.
            # Example: ['BLR', 'EGS', 'SOC', 'SOCC', 'SPO', ...]
            # But interesting topics from the meta may be found in these fields:
            #   - article:section                       ("Aerospace & Defense")
            #   - analyticsAttributes.topicChannel      ("Business")
            #   - analyticsAttributes.topicSubChannel   ("Aerospace & Defense")
            #   - DCSext.ChannelList                    ("Business;Asia Pacific;World")
            topics: List[Optional[str]] = [
                self.precomputed.meta.get("article:section"),
                self.precomputed.meta.get("analyticsAttributes.topicChannel"),
                self.precomputed.meta.get("analyticsAttributes.topicSubChannel"),
            ]
            topics.extend(generic_topic_parsing(self.precomputed.meta.get("DCSext.ChannelList"), delimiter=";"))

            # Remove empty topics and duplicates deterministically
            processed_topics = list(dict.fromkeys(topic for topic in topics if topic))
            return processed_topics

    class V1_1(V1):
        VALID_UNTIL = date.today()

        # TODO: at the end of sports related articles like
        #  https://www.reuters.com/sports/basketball/hot-shooting-suns-wear-down-raptors-2024-03-08/
        #  there is this `--Field Level Media` bloat line
        _paragraph_selector = XPath("(//div[starts-with(@data-testid, 'paragraph')])[position() > 1]")
        _summary_selector = XPath("(//div[starts-with(@data-testid, 'paragraph')])[1]")

        _new_tab_span_selector = XPath(
            "//div[starts-with(@data-testid, 'paragraph')] //span[contains(text(), 'opens new tab')]"
        )

        @function(priority=1)
        def _remove_new_tab_span(self) -> None:
            span: lxml.html.HtmlElement
            for span in self._new_tab_span_selector(self.precomputed.doc):
                span.drop_tree()
