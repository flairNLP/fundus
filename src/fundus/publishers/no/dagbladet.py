import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.data import Image
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_date_parsing,
    generic_nodes_to_text,
    generic_topic_parsing,
    image_extraction,
)


class DagbladetParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath(
            "//main/article/div[@class='article-top expand']//header/h3 | "
            "//main/article/div[contains(@class, 'articleHeader')]/h2 | "
            "(//main/article/div[contains(@class, 'bodytext')]/*)[1][self::div and contains(@class,'factbox')]//p"
        )
        _subheadline_selector = CSSSelector(
            "#main > article > div.body-copy > h2, #main > article > div[class~='bodytext'] > h3"
        )
        _paragraph_selector = CSSSelector(
            "#main > article > div.body-copy > p, #main > article > div[class~='bodytext'] > p"
        )

        _author_selector = CSSSelector("div[itemtype='http://schema.org/Person'] address.name > a")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def authors(self) -> List[str]:
            return generic_nodes_to_text(self._author_selector(self.precomputed.doc), normalize=True)

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("article:tag"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                author_selector=re.compile(r"Foto:(?P<credits>.*)"),
                image_selector=XPath(
                    "//figure[contains(@class, 'image')]//img | "
                    "//article//figure//div[contains(@class,'img')]//img[not(contains(@class, 'lazyload'))]"
                ),
                caption_selector=XPath(
                    "./ancestor::*[self::figure or (self::div and contains(@class,'articleHeader'))]//figcaption"
                ),
            )
