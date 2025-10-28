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


class LBCGroupParser(ParserProxy):
    class V1(BaseParser):
        content_container_selector = XPath("//div[@class='LongDesc']/div[1]/div[1]")
        
        # We tell the parser utility that the content container itself ('.') 
        # should be treated as the main text block, allowing extraction of text nodes.
        _paragraph_selector = XPath(".") 
        
        # There are no subheadlines (like <h2>) in your snippet.
        _subheadline_selector = None 
        
        @attribute
        def body(self) -> Optional[ArticleBody]:
            # Use the defined content_selector to locate the block of text.
            return extract_article_body_with_selector(
                self.precomputed.doc,
                content_selector=self._content_container_selector,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
                # Optionally, remove elements like the banner injection and the 'Reuters' credit 
                # if you want a cleaner body, but we'll focus on text for now.
            )
        
        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")
        
        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))
        
        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                author_selector=XPath("./ancestor::figure//footer"),
                size_pattern=re.compile(r"/rs:fill:(?P<width>[0-9]+):"),
            )
    