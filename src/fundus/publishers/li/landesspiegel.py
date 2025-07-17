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
    transform_breaks_to_paragraphs,
)


class LandesspiegelParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath("//div[contains(@class, 'entry-content')]/p[not(text()) and strong]")
        _paragraph_selector = XPath("//div[contains(@class, 'entry-content')]/p[text()]|//blockquote")
        _subheadline_selector = XPath("//div[contains(@class, 'entry-content')]/h2")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
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
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//h1"),
                image_selector=XPath("//div[@class='post-image']//img"),
                caption_selector=XPath("./ancestor::div[@class='post-image']//div[contains(@class,'caption')]"),
                author_selector=re.compile(r"(?i)\|\s*(Foto|Bild(quelle)?):\s*(?P<credits>.*)$"),
            )
