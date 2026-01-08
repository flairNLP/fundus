import datetime
import re
from typing import List, Optional, Union

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class GolemParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2025, 8, 21)

        _bloat_regex = r"^Dieser Artikel enthält sogenannte Affiliate-Links"
        _summary_selector = XPath("//hgroup/p")
        _paragraph_selector = XPath(
            f"//section /p[not(@class='meta' or re:test(string(), '{_bloat_regex}'))]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _subheadline_selector: Union[XPath, CSSSelector] = CSSSelector("div > section > h2")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
                tag_filter=XPath("self::*[@class='go-vh']"),
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            if title := self.precomputed.meta.get("title"):
                return title.replace(" - Golem.de", "")
            else:
                return None

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("news_keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//article"),
                author_selector=re.compile(r"(?i)\(bild:(?P<credits>.*)\)"),
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()

        _paragraph_selector = XPath("//article//p[not(ancestor::div[@class='go-info-box__content'])]")
        _subheadline_selector = XPath("//article//h2[not(contains(@class, 'teaser'))]")
        _summary_selector = XPath("//div[@class='go-article-header__intro']")
