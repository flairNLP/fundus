import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.data import Image
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class VerdensGangParser(ParserProxy):
    class V1(BaseParser):
        _bloat_pattern: str = "Les også:|" "Vil du lese mer"

        _summary_selector = CSSSelector("header.article-intro p")
        _subheadline_selector = CSSSelector("section.article-body > h2")
        _paragraph_selector = XPath(
            f"//section[contains(@class,'article-body')] /p[not(re:test(string(), '{_bloat_pattern}'))]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )

        _paywall_selector = CSSSelector("#paywall-login-link")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
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
            return generic_topic_parsing(self.precomputed.meta.get("article:tag"))

        @attribute
        def free_access(self) -> bool:
            return not self._paywall_selector(self.precomputed.doc)

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                author_selector=re.compile(r"Foto:(?P<credits>.*)"),
            )
