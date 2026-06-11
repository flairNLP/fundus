import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.data import Image
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class PostMediaParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            "//div[@class='story-v2-content-element-inline']/"
            "p[text() and not(@data-async) and not(text()='National Post')]"
        )
        _subheadline_selector = XPath(
            "//div[@class='story-v2-content-element-inline']/h3 |"
            "//div[@class='story-v2-content-element-inline']/p/strong"
        )
        _summary_selector = CSSSelector("article p.article-subtitle")

        _bloat_topics = {
            "Curated",
            "News",
            "Newsroom daily",
            "story",
            "Canada",
            "World",
            "politics",
            "Business",
            "Travel",
            "Entertainment",
        }
        _topic_filter = re.compile(
            r"([0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}|NLP Entity Tokens|NLP Category|NP Comment|Category):?\s*"
        )

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
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(
                self.precomputed.ld.bf_search("keywords"),
                substitution_pattern=self._topic_filter,
                result_filter=self._bloat_topics,
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("(//div[@class='story-v2-block story-v2-article-container'])[1]"),
                lower_boundary_selector=XPath("//section[@class='article-content__share-group']"),
                caption_selector=XPath("./ancestor::figure/figcaption/span[@class='caption']"),
                author_selector=XPath("./ancestor::figure/figcaption/span[@class='credit' or @class='distributor']"),
            )
