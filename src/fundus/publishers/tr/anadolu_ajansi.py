import datetime
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


class AnadoluAjansiParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("div.detay-bg > div > div > h4")
        _paragraph_selector = XPath(
            "//div[@class='detay-icerik']"
            "//h6[not(ancestor::div[@class='detay-paylas'])] | "
            "//div[@class='detay-icerik']//p"
        )
        _subheadline_Selector = CSSSelector("div.detay-icerik > div:nth-child(2) > h3")
        _author_selector = CSSSelector("div.detay-bg > div > div > div > span:nth-child(1)")
        _date_selector = CSSSelector("div.detay-bg > div > div > div > span.tarih")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_Selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            if authors_list := self._author_selector(self.precomputed.doc):
                if (content := authors_list[0].text) is None:
                    return []
                authors_str = content.replace("|", "")
                return generic_author_parsing(authors_str)
            return []

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            if date_nodes := self._date_selector(self.precomputed.doc):
                if (content := date_nodes[0].text) is None:
                    return None
                match = re.search(r"(\d{2}\.\d{2}\.\d{4})", content)
                if match is None:
                    return None
                return generic_date_parsing(match.group(1))
            return None

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            if keywords_ := (
                generic_topic_parsing(self.precomputed.meta.get("keywords"))
                or generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))
            ):
                if "Anadolu Ajansı" in keywords_:
                    keywords_.remove("Anadolu Ajansı")
                return keywords_
            return []

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=CSSSelector("div.row.detay.container > div.col-md-10 > img," "div img[alt='']"),
                relative_urls=True,
            )
