import datetime
from typing import List, Optional

from lxml.etree import XPath
from lxml.html import HtmlElement

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class SRFParser(ParserProxy):
    class V1(BaseParser):
        _title_selector = XPath("//span[@class='article-title__text']")
        _author_selector = XPath("//span[@itemprop='author']")
        _paragraph_selector = XPath(
            "//section[@class='article-content']//span[@class='blockquote__text'] | "
            "//section[@class='article-content']/p | "
            "//section[@class='article-content']/li | "
            "//section[@class='article-content']/ul/li"
        )
        _summary_selector = XPath("//header[@class='article-header']/p[@class='article-lead']")
        # The last line of the _subheadline_selector does not comply with the format at first glance, but as far as I
        # can see, Fundus only gets a preliminary article version, when crawling live-tickers which only contains the
        # headlines of the elements. Example:
        # https://www.srf.ch/news/international/krieg-im-nahen-osten-israel-noch-unschluessig-ueber-reaktion-auf-irans-angriff
        _subheadline_selector = XPath(
            "//section[@class='article-content']/h2 | "
            "//section[@class='article-content']"
            "//div[@id='ticker']//li//span[@itemprop='headline']"
        )

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            if not (author_nodes := self._author_selector(self.precomputed.doc)):
                return []
            else:
                if len(author_nodes) > 1:
                    author_list = list()
                    for node in author_nodes:
                        for author in node.text_content().split(";"):
                            author_list.append(author)
                    return generic_author_parsing(author_list)
                return generic_author_parsing([name for name in author_nodes[0].text_content().split(";")])

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def title(self) -> Optional[str]:
            if not (title_node := self._title_selector(self.precomputed.doc)):
                return None
            else:
                node: HtmlElement = title_node[0]
                return node.text_content()
