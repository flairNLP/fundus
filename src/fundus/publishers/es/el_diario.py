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


class ElDiarioParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[@class='c-content']//p[@class='article-text']")
        _subheadline_selector = XPath("//div[@class='c-content']//h2[@class='article-text']")
        _summary_selector = XPath(
            "//div[@class='news-header']//ul[@class='footer']//li[not(contains(@class, 'subtitle--hasAnchor'))]/h2[text()]"
        )

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
                upper_boundary_selector=XPath("//div[@class='row row__content']"),
                lower_boundary_selector=XPath("//div[@class='partner-wrapper']"),
                image_selector=XPath("//picture[@class='news-image']//img"),
                caption_selector=XPath("./ancestor::figure//figcaption//span[@class='title']/text()"),
                author_selector=XPath("./ancestor::figure//figcaption//span[@class='title']/span"),
                relative_urls=True,
            )
