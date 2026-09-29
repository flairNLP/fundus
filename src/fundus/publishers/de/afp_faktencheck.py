import datetime
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.data import Image
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_nodes_to_text,
    generic_topic_parsing,
    image_extraction,
)


class AFPFaktencheckParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = XPath("//div[@class='wrapper-summary']")
        _paragraph_selector = XPath("//div[@class='wrapper-body']//p[text()]")
        _subheadline_selector = XPath("//div[@class='wrapper-body']//*[self::h3 or self::h2]")

        _author_parser = XPath("//li[@class='information-item']/span/a")
        _topic_selector = XPath("//div[@class='left-content']/a")
        _image_selector = XPath("//div[contains(@class,'field--type-image')]//img")

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(generic_nodes_to_text(self._author_parser(self.precomputed.doc)))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.xpath_search("//ClaimReview/datePublished", scalar=True))

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(
                generic_nodes_to_text(self._topic_selector(self.precomputed.doc), normalize=True)
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=self._image_selector,
                caption_selector=XPath("./ancestor::div[@class='wrapper-image']//span[@class='legend']"),
                relative_urls=True,
            )
