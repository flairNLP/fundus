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


class HankookIlboParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[@itemprop='articleBody']/p[@class='editor-p']")
        _summary_selector = XPath("//div[@itemprop='articleBody']/h2")
        _subheadline_selector = XPath("//div[@itemprop='articleBody']/h3")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                doc=self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.xpath_search("//NewsArticle/author/name"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("news_keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//div[@itemprop='articleBody']"),
                image_selector=XPath("//div[@itemprop='articleBody']//div[@class='img-box']//img"),
                caption_selector=XPath("./ancestor::div[@class='editor-img-box']//div[@class='caption']"),
                author_selector=re.compile(r"(?!.*\.)(?P<credits>.*)"),
            )
