import re
from datetime import datetime
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


class MBNParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath("//div[@class='mid_title']//div")
        _paragraph_selector = XPath(
                "//div[@itemprop='articleBody']//p"
                " | "
                "//div[@itemprop='articleBody']//div[normalize-space(text())"
                " and not(ancestor::div[@class='mid_title'])]"
        )

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.xpath_search("NewsArticle/author", scalar=True))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.ld.xpath_search("NewsArticle/datePublished", scalar=True))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.xpath_search("NewsArticle/headline", scalar=True)

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//div[@itemprop='articleBody']"),
                image_selector=XPath("//div[@itemprop='articleBody']//div[@class='thumb_area img']//img"),
                caption_selector=XPath("./ancestor::div[@class='thumb_area img']//span[@class='thum_figure_txt']"),
                alt_selector=XPath("./@alt"),
                author_selector = re.compile(
                     r'^\s*(?:<(?P<credits>[^>]+)>|\[?\s*(?:사진\s*=?\s*)?(?P<credits>[^\]\r\n<>]+)\s*\]?)\s*$'
                ),
                
#                author_selector = re.compile(
#                    r'^\s*(?:'
#                    r'<(?P<credits>[^>]+)>'                                     # <OOO 기자>
#                    r'|\[?\s*(?:사진\s*=?\s*)?(?P<credits>[^\]\r\n<>]+)\?'
#                    r'|.*?사진\s*=\s*(?P<credits>[^]\r\n<>]+)'
#                    r')\s*$'
#                )
                
            )

