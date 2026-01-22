import datetime
import re
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class TheCitizenParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[@class='single-content']//p[string-length(text())>2]")
        _summary_selector = XPath("//div[@class='single-excerpt']/h2")
        _subheadline_selector = XPath("//div[@class='single-content']/h2")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
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
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//div[contains(@class, 'featured-image')]/img | //figure/img"),
                caption_selector=XPath(
                    "./ancestor::div[contains(@class, 'featured-image')]//div[contains(@class, 'image-caption')]//p |"
                    "./ancestor::figure//figcaption"
                ),
                author_selector=re.compile(r"(?i)(image courtesy( of)?\s*|image|picture):?(?P<credits>.+)"),
            )
