import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector
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


class LuxemburgerWortParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2026, 5, 5)

        _paragraph_selector = XPath("//p[contains(@class, 'articleParagraph')]")
        _summary_selector = XPath("//h2[contains(@class, 'articleParagraph')]")
        _subheadline_selector = XPath("//h4[contains(@class, 'articleSubheading')]")

        _topic_selector = XPath("//div[contains(@class, 'tag-list')]//a")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(generic_nodes_to_text(self._topic_selector(self.precomputed.doc)))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//figure[not(contains(@class, 'Teaser'))]//img"),
                upper_boundary_selector=CSSSelector("h1"),
                caption_selector=XPath("./ancestor::figure//div[contains(@class, 'ImageCaption')]"),
                author_selector=re.compile(r"(?i)Foto:\s*(?P<credits>.*)"),
            )

    class V2(BaseParser):
        _summary_selector = XPath("//article//h2[contains(@class, 'paragraph')]")
        _paragraph_selector = XPath(
            "//article//section/p[text() or em] | "
            "//article//section/div[contains(@class,'interview_interview')]/p | "
            "//article//section/ul/li | "
            "//article//section/ol/li"
        )
        _subheadline_selector = XPath("//article//section/*[self::h4 or self::h5]")

        _topics_selector = XPath("//div[contains(@class, 'tag-list')]//a")
        _bloat_topics = {"Mosaik", "Sport", "Panorama", "Luxemburg", "Norden", "Osten", "Westen", "Süden"}

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
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
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(
                generic_nodes_to_text(self._topics_selector(self.precomputed.doc), normalize=True),
                result_filter=self._bloat_topics,
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                lower_boundary_selector=XPath("//div[starts-with(@class,'trustbox_trustbox')]"),
                image_selector=XPath("//figure//img[not(contains(@class, 'teaser'))]"),
                caption_selector=XPath(
                    "./ancestor::figure//span[contains(@class, 'caption') and not(contains(@class,'gallery_counter'))]"
                ),
                author_selector=re.compile(r"(?i)Foto:\s*(?P<credits>.*)$"),
            )
