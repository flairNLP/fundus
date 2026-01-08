import re
from datetime import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_nodes_to_text,
    generic_topic_parsing,
    image_extraction,
    strip_nodes_to_text,
)


class KlasseGegenKlasseParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            "//div[@class='singleContent ']/p[not((not(text()) and em) or re:test(string(.), '^Zum Weiterlesen:'))]"
            " | //ol[@class='footnotesList']/li",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _summary_selector = XPath("//p[@class='singleHeader-excerpt']")
        _subheadline_selector = XPath("//div[@class='singleContent ']/h2")

        _publishing_date_selector = XPath("(//div[@class='metaInfoDateTime']/span)[1]")

        _author_selector = XPath("//ul[@class='metaInfoAuthorList']//li")

        _topic_selector = XPath("//ul[@class='singleTagList']//li")

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(strip_nodes_to_text(self._author_selector(self.precomputed.doc)))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(strip_nodes_to_text(self._publishing_date_selector(self.precomputed.doc)))

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(
                generic_nodes_to_text(self._topic_selector(self.precomputed.doc), normalize=True)
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                author_selector=re.compile(r"(?i)(foto|quelle|bild):\s*(?P<credits>.+)"),
            )
