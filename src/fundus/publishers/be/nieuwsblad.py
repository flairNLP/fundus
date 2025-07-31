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
    strip_nodes_to_text,
)


class NieuwsbladParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath("//*[@data-testid='article-intro']")
        _paragraph_selector = XPath("//*[@data-testid='article-body']/p[text()]")
        _subheadline_selector = XPath(
            "//*[@data-testid='article-body']/p/span[@class='bold'] | " "//*[@data-testid='article-body']/h3"
        )

        _topic_selector = XPath("//ul[contains(@class, 'taglist')]/li|//div[contains(@class, 'tag-list')]/a")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            topic_string = strip_nodes_to_text(self._topic_selector(self.precomputed.doc), join_on=",")
            if topic_string is not None:
                return generic_topic_parsing(topic_string, delimiter=",")
            return []

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                image_selector=XPath("//figure[not(contains(@class, 'teaser'))]//img"),
                paragraph_selector=self._paragraph_selector,
                caption_selector=XPath(
                    "./ancestor::figure//*[(self::div and contains(@class, 'caption')) or self::figcaption]"
                ),
                author_selector=re.compile(r"\s*—?\s*©\s*(?P<credits>.*)"),
                lower_boundary_selector=XPath("//div[@class='widget partnerbox_1']"),
            )
