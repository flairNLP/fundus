import datetime
from typing import List, Optional, Union

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class SternParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2024, 10, 26)
        _paragraph_selector: Union[XPath, CSSSelector] = CSSSelector(".article__body >p")
        _summary_selector: Union[XPath, CSSSelector] = CSSSelector(".intro__text")
        _subheadline_selector: Union[XPath, CSSSelector] = CSSSelector(".subheadline-element")

        _topic_selector: Union[XPath, CSSSelector] = CSSSelector(".article__tags li.links__item")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            initial_authors = generic_author_parsing(self.precomputed.ld.bf_search("author"))
            return [el for el in initial_authors if el != "STERN.de"]

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(
                self.precomputed.meta.get(
                    "date",
                )
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            topic_nodes = self._topic_selector(self.precomputed.doc)
            return [node.text_content().strip("\n ") for node in topic_nodes]

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()
        _summary_selector = XPath("//div[@class='intro typo-intro u-richtext']")
        _paragraph_selector = XPath("//div[@class='article__body']//p[contains(@class,'typo-body-default')]")
        _subheadline_selector = XPath("//div[@class='article__body']//h2[@class='subheadline-element typo-headline2']")

        _topic_selector = XPath("//ul[@class='tags typo-topic-tag u-blanklist']/li")
