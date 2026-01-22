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


class TimesLiveParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2025, 9, 30)

        _paragraph_selector = XPath("//div[@class='wrap']//div[@class='text']/p[span or text()]")
        _summary_selector = XPath("//h3[contains(@class, 'article-title-tertiary')] ")
        _subheadline_selector = XPath("//div[@class='wrap']//div[@class='text']/h3")

        _bloat_topics = {
            "reuters",
            "timeslive",
            "Breaking news",
            "general",
            "politics",
            "sport",
            "entertainment",
            "lifestyle",
            "weird",
            "world",
            "africa",
            "news",
            "extra",
            "Sunday times",
            "times",
            "the times",
            "business times",
            "tshisa live",
        }

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"), result_filter=self._bloat_topics)

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                lower_boundary_selector=XPath("//div[@class='wrap']//hr"),
                upper_boundary_selector=XPath("//h1"),
                image_selector=XPath("//div[contains(@class, 'image-container')]//img"),
                caption_selector=XPath(
                    "./ancestor::div[contains(@class, 'image-container')]//span[@class='description']"
                ),
                author_selector=XPath("./ancestor::div[contains(@class, 'image-container')]//span[@class='name']"),
                relative_urls=True,
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()

        _paragraph_selector = XPath("//article/p[not(string()='TimesLIVE')]")  # There are no subheadlines/summaries

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                lower_boundary_selector=XPath("//div[@class='wrap']//hr"),
                upper_boundary_selector=XPath("//h1"),
                caption_selector=XPath("./ancestor::figure//span[contains(@class, 'caption')]"),
                author_selector=XPath("./ancestor::figure//span[contains(@class, 'credit')]"),
                relative_urls=True,
            )
