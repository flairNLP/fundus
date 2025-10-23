import datetime
import re
from typing import List, Optional, Union

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


class NDRParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2025, 6, 16)

        _paragraph_selector = XPath(
            "//div[@class='modulepadding copytext']/p[not(@class='textauthor' or @class='preface')] "
            "| //div[@class='modulepadding copytext']/ul/li"
        )
        _summary_selector: Union[XPath, CSSSelector] = CSSSelector(".preface")
        _subheadline_selector: Union[XPath, CSSSelector] = CSSSelector("article .modulepadding > h2")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("title")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//div[@id='page']"),
                image_selector=XPath(
                    "//div[@id='page']//*[(self::div and not(@class='teaserimage')) or (self::a and @class='zoomimage')]/div[contains(@class,'image-container')]//picture//img"
                ),
                relative_urls=XPath("string(//link[@rel='canonical']/@href)"),
                caption_selector=XPath("./ancestor::div[contains(@class,'contentimage')]//span[@class='caption']"),
                author_selector=re.compile(r"(?i)©\s*(ndr)?\s*(foto)?:?\s*(?P<credits>.+)"),
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()

        _paragraph_selector = XPath("//article/p[not(@class='textauthor')] | //article/ul/li | //article/blockquote")
        _subheadline_selector = XPath("//article/h2")
        _summary_selector = XPath("//header/p[@class='preface']")

        _bloat_keywords = ["hh", "regionalmeldungen", "News", "kurzmeldungen"]

        @attribute
        def topics(self) -> List[str]:
            return [
                topic
                for topic in generic_topic_parsing(self.precomputed.meta.get("keywords"))
                if topic not in self._bloat_keywords
            ]

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//article"),
                relative_urls=XPath("string(//link[@rel='canonical']/@href)"),
                image_selector=XPath(
                    "//article//div[contains(@class,'contentimage') or contains(@class, 'herocontainer')]//picture//img"
                ),
                caption_selector=XPath(
                    "./ancestor::div[contains(@class,'contentimage')]//span[contains(@class, 'caption')]"
                ),
                author_selector=re.compile(r"(?i)©\s*(ndr)?\s*(foto)?:?\s*(?P<credits>.+)"),
            )
