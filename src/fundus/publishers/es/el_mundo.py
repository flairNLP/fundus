import datetime
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


class ElMundoParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[@class='ue-c-article__body']/p")
        _subheadline_selector = XPath("//div[@class='ue-c-article__body']/h2")
        _summary_selector = XPath("//div[@class='ue-c-article__standfirst']//p")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def topics(self) -> List[str]:
            return [topic.split("/")[-1] for topic in generic_topic_parsing(self.precomputed.meta.get("keywords"))]

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//figure//img[contains(@class, 'article__image')]"),
                caption_selector=XPath("./ancestor::figure//figcaption//span[contains(@class, 'description')]"),
                author_selector=XPath("./ancestor::figure//figcaption//span[contains(@class, 'source')]/span"),
            )
