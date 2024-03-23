import datetime
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class HeiseParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath(
            "//article[not(@data-component='TeaserContainer')]//p[@class='a-article-header__lead']"
        )
        _subheadline_selector = XPath("//article[not(@data-component='TeaserContainer')]//h3[@class='subheading']")
        _paragraph_selector = XPath(
            "//div[@class='article-layout__content article-content']//p[not(@class"
            " or ((string-length(text()) < 3) and (contains(text(), '(') or contains(span, '(')))"
            " or contains(text(), '=== Anzeige / Sponsorenhinweis')"
            " or contains(text(), 'Tipp: Wir sind bei WhatsApp!')"
            " or contains(a, 'heise+ abonnieren')"
            " or contains(text(), '► '))"
            " or @class='antwort rte__abs--antwort'"
            " or @class='frage rte__abs--frage'] "
            " | //div[@class='article-layout__content article-content']//ul["
            "@class='rte__list rte__list--unordered' or @class='boxtext']"
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
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))
