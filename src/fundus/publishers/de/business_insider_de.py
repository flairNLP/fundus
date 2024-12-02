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


class BusinessInsiderDEParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("article div.bi-bulletpoints li, article div.bi-bulletpoints > p")
        _subheadline_selector = CSSSelector("article > div > h2, article > div > h3")
        _paragraph_selector = XPath(
            """
            //article
            //div[
                contains(@class, 'article-body') 
                or contains(@class, 'piano-article')]
            /p[
                not(ancestor::*[@class='bi-bulletpoints']
                    or mark[@class='has-inline-color has-cyan-bluish-gray-color']
                    or @class='has-text-align-right')]
            """
        )

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
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords")) or generic_topic_parsing(
                self.precomputed.ld.bf_search("keywords")
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//img[not(contains(@class, 'size-thumbnail-square'))]"),
            )
