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


class TokyoChunichiShimbunParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[@class='block' and not(descendant::div or descendant::h2)]")
        _subheadline_selector = XPath("//div[@class='block']//h2")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.bf_search("articleSection"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                image_selector=CSSSelector("main div.image img, main div.thumb img"),
                caption_selector=XPath(
                    "./ancestor::div[@class='wrap']//p[@class='caption'] | "
                    "./ancestor::div[@class='thumb']//p[@class='thumb-caption']"
                ),
                author_selector=re.compile(r"（(?P<credits>[^）]+)）\s*$"),
                paragraph_selector=self._paragraph_selector,
                relative_urls=True,
            )
