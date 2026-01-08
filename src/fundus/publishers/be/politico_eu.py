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
    image_extraction,
)


class PoliticoEuParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector(".article__content p, .sidebar-grid_content p")
        _subheadline_selector = CSSSelector(".article__content h3, .sidebar-grid__content h3")
        _summary_selector = CSSSelector("p.hero__excerpt")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
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
            keywords_string = self.precomputed.meta.get("keywords")

            if keywords_string is None:
                return []

            return keywords_string.split(",")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                upper_boundary_selector=CSSSelector("article"),
                image_selector=CSSSelector("figure img"),
                paragraph_selector=self._paragraph_selector,
                caption_selector=XPath("./ancestor::figure//div[contains(@class, 'figcaption__inner')]"),
                author_selector=re.compile(r"\|(?P<credits>.*)$"),
            )
