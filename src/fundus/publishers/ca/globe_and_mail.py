import datetime
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


class TheGlobeAndMailParser(ParserProxy):
    class V1(BaseParser):
        _subheadline_selector = CSSSelector("article > h4")
        _paragraph_selector = CSSSelector("article > p")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
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
            topic_list = [topic.lower() for topic in generic_topic_parsing(self.precomputed.meta.get("keywords"))]
            topic_set = set(topic_list)
            topic_duplicates = list(topic_list)
            for element in topic_set:
                topic_duplicates.remove(element)
            for duplicate in topic_duplicates:
                topic_list.remove(duplicate)
            return [topic.title() for topic in topic_list if "news" not in topic]

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                caption_selector=XPath("./ancestor::figure//figcaption//p[@class='figcap-text']/span[1]"),
                author_selector=XPath("./ancestor::figure//figcaption//p[@class='figcap-text']/span[last()]"),
            )
