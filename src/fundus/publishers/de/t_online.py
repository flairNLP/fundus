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


class TOnlineParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[@data-testid='ArticleBody.StreamLayout']//p[@class='text-18 leading-17']")
        _summary_selector = XPath(
            "//div[@data-testid='ArticleBody.StreamLayout']//p[@class='font-bold text-18 leading-17']"
        )

        _subheadline_selector = XPath("//div[@data-testid='ArticleBody.StreamLayout']//h3")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
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
            return [t for t in generic_topic_parsing(self.precomputed.meta.get("keywords")) if not t.isdigit()]

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                image_selector=XPath("//figure/*[self::div or self::a]/img"),
                paragraph_selector=self._paragraph_selector,
                author_selector=re.compile(r"(?i)\(quelle:\s*(?P<credits>.+)\)$"),
                relative_urls=True,
            )
