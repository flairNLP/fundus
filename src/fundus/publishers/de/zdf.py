import datetime
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


class ZDFParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("div.r1nj4qn5")
        _summary_selector = CSSSelector("p.c1bdz7f4")
        _subheadlines_selector = CSSSelector("h2.hhhtovw")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadlines_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath(
                    "//picture//img[not(contains(@class, 'error') or contains(@src, 'zdfheute-whatsapp-channel'))]"
                ),
                caption_selector=XPath("./ancestor::div[@class='c1owvrps c10o8fzf']//span[@class='c1pbsmr2']"),
                lower_boundary_selector=XPath("//div[@class='s1am5zo f1uhhdhr']"),
            )
