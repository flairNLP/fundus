import datetime
import re
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    image_extraction,
)


class LaVanguardiaParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            "//div[@class='article-modules']//p[@class='paragraph'] | "
            "//div[@class='widget' and not(@id)]//p[not(@class='creditos')]"
        )
        _subheadline_selector = XPath(
            "//div[@class='article-modules']//h3[@class='subtitle'] | "
            "//div[@class='widget' and not(@id)]//h2|//span[@class='ubicacion']"
        )
        _summary_selector = XPath("//h2[@class='epigraph']|//div[@id='slide-content-1']/p")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("title")

        @attribute
        def authors(self) -> List[str]:
            return [
                re.sub(r"(?u)\s*\u200b.*", "", author)
                for author in generic_author_parsing(self.precomputed.ld.bf_search("author"))
            ]

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//figure[contains(@class,'composite-image')]//img"),
                caption_selector=XPath("./ancestor::figure//figcaption/p"),
                author_selector=XPath("./ancestor::figure//figcaption/span"),
                relative_urls=True,
            )
