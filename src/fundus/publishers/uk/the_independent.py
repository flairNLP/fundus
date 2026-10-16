import datetime
import json
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


class TheIndependentParser(ParserProxy):
    class V1(BaseParser):
        # Standard articles are contained in div#main. Bulletin articles consist of a bullet list following the
        # headline, which is only wrapped in div#main since ~09/2025. IndyBest reviews are either standard articles
        # or split into div#product-top-content, one container per reviewed product and div#product-bottom-content.
        _summary_selector = XPath("//header[@id='articleHeader']//h1/following-sibling::p[1]")
        _subheadline_selector = XPath(
            """
            //div[@id='main']/div[not(contains(@class, 'related'))]/*[(self::h2 or self::h3) and normalize-space()]
            | //div[@id='product-top-content']/h2
            | //div[@id='product-top-content']//article//header/h3
            | //*[starts-with(@id, 'productId_')]/header//h2
            | //div[@id='product-bottom-content']/div/h2[not(starts-with(normalize-space(), 'Why you can trust'))]
            """
        )
        _paragraph_selector = XPath(
            """
            (
                //div[@id='main']/p
                | //div[@id='main']/div/*[(self::ul or self::ol) and not(@class)]/li
                | //div[.//h1]/following-sibling::div/ul[not(@class)]/li
                | //div[@id='product-top-content']/p
                | //div[@id='product-top-content']/*[(self::ul or self::ol) and not(@class)]/li
                | //div[@id='product-top-content']//article//header/following-sibling::div//p
                | //*[starts-with(@id, 'productId_')]//div[contains(@id, '_content__')]//p
                | //div[@id='product-bottom-content']/div/p[
                    not(preceding-sibling::h2[1][starts-with(normalize-space(), 'Why you can trust')])
                ]
                | //div[@id='product-bottom-content']/div/*[(self::ul or self::ol) and not(@class)]/li
            )[not(starts-with(normalize-space(), 'Read more:'))]
            """
        )

        # product headings of IndyBest reviews are prefixed with their rank, e.g. <h2><div>1</div>Product</h2>
        _heading_rank_filter = XPath("self::div[parent::h2]")

        _topic_bloat_pattern = re.compile(
            r"^(Internal\b.*|Bulletin|The Conversation|PA Ready|Independent Premium|indybest)$", re.IGNORECASE
        )

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
                tag_filter=self._heading_rank_filter,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            keywords = self.precomputed.meta.get("keywords")
            if keywords and keywords.lstrip().startswith("["):
                # keywords are given either comma separated or as JSON encoded array, e.g. '["Florida","Miami"]'
                keywords = json.loads(keywords)
            return generic_topic_parsing(keywords, result_filter=self._topic_bloat_pattern)

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=CSSSelector("figure > div > img, div[data-gallery-length] > img"),
                upper_boundary_selector=XPath("//article | //div[@id='main'] | //div[@id='articleContent']"),
                author_selector=re.compile(r"(?P<credits>(\([^)]*\)\s?)+$)"),
            )
