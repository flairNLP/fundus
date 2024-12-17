import datetime
import re
from typing import List, Optional

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


class SportSchauParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector(
            "p[class='textabsatz columns twelve  m-ten  m-offset-one l-eight l-offset-two']" " > strong"
        )
        _paragraph_selector = CSSSelector("article >p.textabsatz:not(p.textabsatz:nth-of-type(1))")
        _subheadline_selector = CSSSelector("article >h2")

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
            return generic_author_parsing(self.precomputed.meta.get("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(
                self.precomputed.meta.get(
                    "date",
                )
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//article//picture[not(contains(@class,'--list'))]//img"),
                lower_boundary_selector=XPath("//div[contains(@class, 'back-to-top')]"),
                alt_selector=XPath("./@title"),
                author_selector=re.compile(r"\|(?P<credits>.+)"),
                caption_selector=XPath(
                    "./ancestor::div[contains(@class, 'absatzbild ')]/div[@class='absatzbild__info']"
                ),
                size_pattern=re.compile(r"/[\dx]+-(?P<width>[0-9]+)/"),
            )
