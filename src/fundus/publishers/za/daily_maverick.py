import datetime
import re
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


class DailyMaverickParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            "//div[contains(@class,' mode-content article-content ')]"
            "//p[(span or a and not(b)) or (text() and not(re:test(string(.), '^([A-Z ]+|Read more:.*)$')))]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _summary_selector = XPath("(//h2[@class='first-paragraph'])[1]")
        _subheadline_selector = XPath(
            "//div[contains(@class,' mode-content article-content ')]//h4 | "
            "//div[contains(@class,' mode-content article-content ')]//p[re:test(string(.), '^[A-Z ]+$')]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )

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
            return [
                t for t in generic_topic_parsing(self.precomputed.ld.bf_search("keywords")) if t not in self.authors()
            ]

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//h1"),
                image_selector=XPath(
                    "//div[contains(@class, 'article-body')]/img | //div[contains(@class, 'wp-caption')]/img"
                ),
                caption_selector=XPath(
                    "./self::img[contains(@class, 'header-image')]/ancestor::div[contains(@class, 'article-body')]//div[@class='image-caption'] |"
                    "./ancestor::div[contains(@class, 'wp-caption')]//p[@class='wp-caption-text']"
                ),
                author_selector=re.compile(r"(?i)\(photo:(?P<credits>.+)\)"),
            )
