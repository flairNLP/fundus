import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.data import Image
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class ExpressenParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("div.article__body-text p")
        _summary_selector = CSSSelector("div.article__preamble")
        _subheadline_selector = CSSSelector("div.article__body-text h2")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//figure//img"),
                caption_selector=XPath("./ancestor::figure//figcaption//div[@class='rich-image__description']"),
                author_selector=XPath("./ancestor::figure//figcaption//div[@class='rich-image__credit']"),
                upper_boundary_selector=CSSSelector("div.article__body-text"),
            )

        @attribute
        def topics(self) -> List[str]:
            return [topic.split("/")[-1] for topic in generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))]
