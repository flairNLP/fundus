import pdb
import re
from datetime import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import (
    ArticleBody,
    BaseParser,
    Image,
    ParserProxy,
    attribute,
    function,
)
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
    transform_breaks_to_paragraphs,
)


class MBNParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[@itemprop='articleBody']//p[normalize-space()]")
        _full_text_selector = XPath("//div[@itemprop='articleBody']")

        @function(priority=0)
        def _transform_br_element(self):
            nodes = self._full_text_selector(self.precomputed.doc)
            if not nodes or len(nodes) != 1:
                return
            element = nodes[0]

            if element.xpath(".//p[normalize-space()]"):
                return

            for ad in element.xpath(".//div[contains(@class,'ad_wrap')]"):
                parent = ad.getparent()
                if parent is not None:
                    parent.remove(ad)

            transform_breaks_to_paragraphs(element, __class__="br-wrap")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.xpath_search("NewsArticle/author", scalar=False))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.ld.xpath_search("NewsArticle/datePublished", scalar=True))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.xpath_search("NewsArticle/headline", scalar=True)

        @attribute
        def images(self) -> List[Image]:
            imgs = image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//div[@itemprop='articleBody']"),
                image_selector=XPath("//div[@itemprop='articleBody']//div[@class='thumb_area img']//img"),
                caption_selector=XPath("./ancestor::div[@class='thumb_area img']" "//span[@class='thum_figure_txt']"),
                alt_selector=XPath("./@alt"),
                author_selector=re.compile(r"^(?!.*)"),
            )

            pattern = re.compile(
                r"\[사진(?:\s*출처)?\s*=\s*([^\]]+)\]" r"|<\s*([^>]+?)\s*기자\s*>" r"|사진\s*=\s*([^.\]\r\n<>]+)"
            )
            for img in imgs:
                text = img.caption or img.description or ""
                raw = [a or b or c for a, b, c in pattern.findall(text)]
                img.authors = list(dict.fromkeys([s.strip() for s in raw if s.strip()]))

            return imgs
