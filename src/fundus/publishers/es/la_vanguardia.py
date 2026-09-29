import datetime
import re
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
)


class LaVanguardiaParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2026, 7, 1)

        _paragraph_selector = XPath(
            "//div[@class='article-modules']//p[@class='paragraph'] | "
            "//div[@class='widget' and not(@id)]//p[not(@class='creditos')]"
        )
        _subheadline_selector = XPath(
            "//div[@class='article-modules']//h3[@class='subtitle'] | "
            "//div[@class='widget' and not(@id)]//h2|//span[@class='ubicacion']"
        )
        _summary_selector = XPath("//h2[@class='epigraph']|//div[@id='slide-content-1']/p")

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
            return self.precomputed.meta.get("title")

        @attribute
        def authors(self) -> List[str]:
            return [
                re.sub(r"(?u)\s*\u200b.*", "", author)
                for author in generic_author_parsing(self.precomputed.ld.bf_search("author"))
            ]

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//figure[contains(@class,'composite-image')]//img"),
                caption_selector=XPath("./ancestor::figure//figcaption/p"),
                author_selector=XPath("./ancestor::figure//figcaption/span"),
                relative_urls=True,
            )

    class V2(BaseParser):
        _summary_selector = XPath("//h2[@class='subtitle dot']")
        _paragraph_selector = XPath("//div[@class='article_story']/p")
        _subheadline_selector = XPath(
            "//div[@class='article_story']/div[@class='content_component highlight']/h3[@class='title'] | "
            "//h3[contains(@class, 'block-headline')]"
        )

        _topic_selector = XPath("(//div[@class='tags-container collapse'])[1]/ul/li")

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
            return self.precomputed.meta.get("og:title")

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(
                generic_nodes_to_text(self._topic_selector(self.precomputed.doc), normalize=True)
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                image_selector=XPath("//figure[not(contains(@class, 'related') or contains(@class, 'author'))]//img"),
                paragraph_selector=self._paragraph_selector,
                caption_selector=XPath("./ancestor::figure//figcaption/span[@class='caption_text']"),
                author_selector=XPath("./ancestor::figure//figcaption/span[@class='caption_author']"),
            )
