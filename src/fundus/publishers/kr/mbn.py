import re
from fundus.parser import ParserProxy, BaseParser, attribute, ArticleBody, Image
from lxml.cssselect import CSSSelector
from lxml.etree import XPath
from typing import Optional, List
from datetime import datetime
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

        _paragraph_selector = XPath("//div[@itemprop='articleBody']//p | //div[@itemprop='articleBody']//div[normalize-space(text())]")
        #_paragraph_selector = XPath("//div[@itemprop='articleBody']//p | //div[@itemprop='articleBody']//div")
        
        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc, 
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.get_value_by_key_path(["NewsArticle", "author"]))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.ld.get_value_by_key_path(["NewsArticle", "datePublished"]))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.get_value_by_key_path(["NewsArticle", "headline"])

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("article:section"))

        @attribute
        def images(self) -> List[Image]:
                 return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//div[@itemprop='articleBody']"),
                image_selector=XPath("//div[@itemprop='articleBody']//div[@class='thumb_area img']//img"),
                caption_selector=XPath("./ancestor::div[@class='thumb_area img']//span[@class='thum_figure_txt']"),
                author_selector=re.compile(r"(?!.*\.)(?P<credits>.*)"),
            )
