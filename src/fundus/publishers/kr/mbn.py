from fundus.parser import ParserProxy, BaseParser, attribute, ArticleBody
from lxml.cssselect import CSSSelector
from lxml.etree import XPath
from typing import Optional, List
from datetime import datetime
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)

class MBNParser(ParserProxy):
    class V1(BaseParser):
        
        _summary_selector = XPath("//div[@class='mid_title']//div")
        _paragraph_selector = XPath("//div[@itemprop='articleBody']//p | //div[@class='article-body']//div[contains(@class, 'rtext') and normalize-space(text())]")
        #_paragraph_selector = XPath("//div[@itemprop='articleBody']//p")

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
