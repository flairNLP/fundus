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


class DailyMailParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("div[itemprop='articleBody'] > p")
        _summary_selector = CSSSelector("#js-article-text > h1")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
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
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            filtered_topics = []
            for topic in generic_topic_parsing(self.precomputed.meta.get("keywords")):
                if topic.casefold() != topic:
                    filtered_topics.append(topic)
            return filtered_topics

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=CSSSelector("div#content"),
                image_selector=CSSSelector("div.mol-img-group img"),
                caption_selector=XPath("./ancestor::div[contains(@class, 'mol-img-group')]/p[@class='imageCaption']"),
            )
