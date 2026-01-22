import datetime
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    image_extraction,
)


class ZwanzigMinutenParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2025, 10, 5)

        _summary_selector = XPath(
            "//div[@class='Article_elementLead__N3pGr']/p | (//div[@type='typeInfoboxSummary'])[1]//li"
        )
        _subheadline_selector = XPath("//section[@class='Article_body__60Liu']//h2[contains(@class, 'crosshead')]")
        _paragraph_selector = XPath("//div[@class='Article_elementTextblockarray__WNyan']/p")

        _caption_selector = XPath("./ancestor::figure//figcaption/span[@class='sc-d47814d6-2 bDLFoO']/p")
        _author_selector = XPath("./ancestor::figure//figcaption/span[@class='sc-d47814d6-3 bmEwwn']")

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
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//article"),
                caption_selector=self._caption_selector,
                author_selector=self._author_selector,
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()

        _summary_selector = XPath("//div[@type='lead']/p | //div[@type='infobox'][1]//li")
        _paragraph_selector = XPath("//section//p[@type='textBlockArray']")
        _subheadline_selector = XPath("//section//h2[@data-testid='Crosshead']")

        _caption_selector = XPath("./ancestor::figure//figcaption/span[@class='sc-b3c65b9d-2 drRlrY']")
        _author_selector = XPath("./ancestor::figure//figcaption/span[@class='sc-b3c65b9d-3 eEeXhh']")
