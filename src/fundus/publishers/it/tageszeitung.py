import datetime
import re
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_date_parsing,
    image_extraction,
)


class TageszeitungParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath("//div[@id='article_content']//p[not(@class='wp-caption-text' or text()) and strong]")
        _paragraph_selector = XPath("//div[@id='article_content']//p[not(@class='wp-caption-text') and text()]")

        _date_selector = XPath("//span[@class='meta_date']//strong/text()")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return re.sub(
                r"(?i)\s*-\s*Die Neue Südtiroler Tageszeitung$", "", self.precomputed.meta.get("og:title") or ""
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            if not (publishing_date := self._date_selector(self.precomputed.doc)):
                return None
            else:
                return generic_date_parsing(publishing_date[0])

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//div[@id='article_content']"),
                image_selector=XPath("//article//img"),
                caption_selector=XPath("./ancestor::div[@class='wp-caption alignnone']//p[@class='wp-caption-text']"),
                author_selector=re.compile(r"(^|\()(Fotos?:|©)(?P<credits>[^)]+)\)?"),
            )
