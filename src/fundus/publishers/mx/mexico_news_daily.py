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


class MexicoNewsDailyParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2026, 7, 27)

        _paragraph_selector = XPath("//div[@class='tdb-block-inner td-fix-index']/p[text()] ")

        _bloat_topics = {"editors_pick"}

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return [
                topic
                for topic in generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))
                if topic not in self._bloat_topics
            ]

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//h1"),
                author_selector=re.compile(r"\((?P<credits>.*?)\)\s*$"),
            )

    class V1_1(V1):
        # trailing italic paragraphs hold author bios and editor's notes. <em> ones are already
        # dropped by extract_article_body_with_selector; this covers the <i> variant as well.
        _trailing_bio = "(i or em) and not(normalize-space(text())) and not(following-sibling::p[normalize-space()])"
        _bloat_pattern = r"^(Sources?:|With reports from|By Mexico News Daily|Mexico News Daily\s*$)"
        _paragraph_selector = XPath(
            f"//div[@class='tts_content_wrapper_1']"
            f"/p[normalize-space()"
            f" and not(re:test(normalize-space(), '{_bloat_pattern}'))"
            f" and not({_trailing_bio})]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
