import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
)


class TheBBCParser(ParserProxy):
    class V1(BaseParser):
        _subheadline_selector = CSSSelector("div[data-component='subheadline-block']")
        _summary_selector = CSSSelector("div[data-component='text-block'] p:first-child b")
        _paragraph_selector = XPath(
            "//div[@data-component='text-block'][1]//p[not(b) or position() > 1] "
            "| //div[@data-component='text-block'][position()>1]//p"
        )

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            article_type = self.precomputed.ld.serialize().keys()
            if "Article" in article_type:
                authors = self.precomputed.ld.get_value_by_key_path(["Article", "author", "name"])
                return generic_author_parsing(authors)
            if "ReportageNewsArticle" in article_type:
                author_objects = self.precomputed.ld.get_value_by_key_path(["ReportageNewsArticle", "author"])
                authors = []
                for obj in author_objects or []:
                    authors.extend(generic_author_parsing(obj.get("name", "")))
                return authors
            return []

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            related_topics_selector = CSSSelector("div[data-component='topic-list'] > div > div > ul > li")
            topics = [str(node.text_content()) for node in related_topics_selector(self.precomputed.doc)]
            return topics
