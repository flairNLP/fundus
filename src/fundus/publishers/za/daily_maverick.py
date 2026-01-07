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


class DailyMaverickParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2025, 11, 19)
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
                t
                for t in generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))
                if t.lower() not in [a.lower() for a in self.authors()]
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

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()

        _summary_selector = XPath("//div[contains(@class,'top-summary')] /p")
        _paragraph_selector = XPath(
            r"//div[contains(@class,'article-content')]"
            r"//p[text() and not(re:test(string(.), '^(By ([A-z-.]+\s*){1,4}|Read more:.*)$'))] |"
            r"//div[contains(@class,'article-content')] //ul /li",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _subheadline_selector = XPath("//div[contains(@class,'article-content')] //h3")

        _author_selector = XPath(
            r"//div[contains(@class,'article-content')]//p[re:test(string(.), '^By ([A-z-]+\s*){1,4}$')]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )

        @attribute
        def authors(self) -> List[str]:
            if authors := self._author_selector(self.precomputed.doc):
                return generic_author_parsing(
                    generic_nodes_to_text(authors), substitution_pattern=re.compile(r"(?i)^by\s*")
                )
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//h1"),
                image_selector=XPath("(//figure | //div[contains(@class, 'main-image')])//img"),
                caption_selector=XPath(
                    "./ancestor::figure//figcaption |"
                    "./ancestor::div[contains(@class, 'main-image')]//em[@class='image-caption']"
                ),
                author_selector=[
                    re.compile(r"(?i)\(photo:(?P<credits>[^)]+)\)"),
                    re.compile(r"(?P<credits>[A-Z /]+$)"),
                ],
            )
