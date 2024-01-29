import datetime
import re
from typing import List, Optional, Pattern

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    apply_substitution_pattern_over_list,
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class BSZeitungParser(ParserProxy):
    class V1(BaseParser):
        _author_substitution_pattern: Pattern[str] = re.compile(r"FUNKE Mediengruppe")
        _paragraph_selector = XPath(
            "//div[@class='article-body']//p[not(contains(strong, 'Meistgeklickte Nachrichten "
            "aus der Region') or contains(strong, 'Keine wichtigen News mehr verpassen') or "
            "@rel='author' or em[@class='print'] or contains(a, 'Jetzt Angebot und Vorteile "
            "checken') or contains(text(), 'Lesen Sie mehr Geschichten aus')  or contains("
            "strong, 'Mehr wichtige Nachrichten aus') or contains(strong, 'Täglich wissen, "
            "was in') or contains(strong, 'Auch interessant') or contains(strong, 'Das könnte "
            "Sie auch interessieren') or contains(strong, 'Lesen Sie auch') or contains("
            "strong, 'Mehr zu dem Thema') or contains(strong, 'Mehr zum Thema') or contains("
            "strong, 'Lesen Sie dazu') or contains(strong, 'Lesen Sie hier'))]"
        )
        _summary_selector = XPath("//div[@class='article-body']//p[1]")
        _subheadline_selector = XPath(
            "//div[@class='article-body']//h3[not(contains(text(), 'Alle Artikel der "
            "Serie') or contains(text(), 'Mehr zum Thema') or contains(text(), "
            "'weitere Videos') or contains(text(), 'Auch interessant') or contains(text(), "
            "'Weitere News'))]"
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
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))

        @attribute
        def authors(self) -> List[str]:
            return apply_substitution_pattern_over_list(
                generic_author_parsing(self.precomputed.ld.bf_search("author")), self._author_substitution_pattern
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute(validate=False)
        def free_access(self) -> bool:
            return self.precomputed.ld.bf_search("isAccessibleForFree") == "True"
