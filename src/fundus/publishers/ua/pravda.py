import re
from datetime import datetime
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_nodes_to_text,
    generic_topic_parsing,
    image_extraction,
    strip_nodes_to_text,
)


class PravdaParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            "//article[contains(@class,'post')]//p[(text() or span[not(strong)]) and not(strong[em])]"
        )
        _subheadline_selector = XPath("//article[contains(@class,'post')]//h2")

        _author_selector = XPath("//span[@class='post_news_author']|//p/strong/em")
        _topic_selector = XPath("//div[@class='post_news_tags']/a")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.xpath_search("//headline", scalar=True)

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(strip_nodes_to_text(self._author_selector(self.precomputed.doc)))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.ld.xpath_search("//datePublished", scalar=True))

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
                image_selector=XPath("//div[contains(@class, 'post_') or contains(@class, 'image')]/picture//img"),
                caption_selector=XPath(
                    "./ancestor::div[contains(@class, 'post_') or contains(@class, 'image')]/div[@class='post_news_photo_captain']"
                ),
                author_selector=XPath(
                    "./ancestor::div[contains(@class, 'post_') or contains(@class, 'image')]/div[contains(@class,'source') or contains(@class,'author')]"
                ),
                upper_boundary_selector=XPath("//article"),
                lower_boundary_selector=self._topic_selector,
            )
