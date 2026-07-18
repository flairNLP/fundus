import datetime
import re
from typing import List, Optional, Pattern

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute, function
from fundus.parser.utility import (
    apply_substitution_pattern_over_list,
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_text_extraction_with_css,
    generic_topic_parsing,
    image_extraction,
    strip_nodes_to_text,
)


class MDRParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2026, 6, 1)

        _author_substitution_pattern: Pattern[str] = re.compile(r"MDR \w*$|MDR \w*-\w*$|MDRfragt-Redaktionsteam|^von")
        # regex examples: https://regex101.com/r/2DSjAz/1
        _source_detection: str = r"^((MDR (AKTUELL ){0,1}\(([A-z]{2,3}(\/[A-z]{2,3})*|[A-z, ]{2,50}))\)|(Quell(e|en): (u.a. ){0,1}[A-z,]{3,4})|[A-z]{2,4}(, [A-z]{2,4}){0,3}( \([A-z]{2,4}\)){0,1}$|[A-z]{2,4}\/[A-z(), \/]{3,10}$)"
        _paragraph_selector = XPath(
            f"//div[contains(@class, 'paragraph')]"
            f"/p[not(re:test(em, '{_source_detection}') or re:test(text(), '{_source_detection}'))]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _summary_selector = CSSSelector("p.einleitung")
        _subheadline_selector = CSSSelector("div > h3.subtitle")
        _author_selector = CSSSelector(".articleMeta > .author")

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
            if self.precomputed.meta.get("news_keywords") is not None:
                return generic_topic_parsing(self.precomputed.meta.get("news_keywords"))
            else:
                return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            if raw_author_str := generic_text_extraction_with_css(self.precomputed.doc, self._author_selector):
                raw_author_str = raw_author_str.replace(" und ", ", ")
                author_list = [name.strip() for name in raw_author_str.split(",")]
                return apply_substitution_pattern_over_list(author_list, self._author_substitution_pattern)

            return []

        @attribute
        def title(self) -> Optional[str]:
            return title if isinstance(title := self.precomputed.ld.bf_search("headline"), str) else None

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//div[@id='content']"),
                image_selector=XPath("//div[contains(@class,'mediaCon ') and not(@data-ctrl-player)]//noscript/img"),
                caption_selector=XPath("./ancestor::div[@class='media mediaA ']//span[@class='mediaSubtitle']"),
                author_selector=XPath("./ancestor::div[@class='media mediaA ']//span[@class='mediaRights copyright']"),
            )

    class V2(BaseParser):
        _summary_selector = XPath("//header/p[@class='preface']")
        _paragraph_selector = XPath(""
                                    "//article/p[string-length(@class)<1 and text()] | "
                                    "//article/ul/li[text()] |"
                                    "//article/blockquote"
                                    )
        _subheadline_selector = XPath("//article/h2")

        _blockquote_text_content_selector = XPath("//article/blockquote/span/em")

        _headline_selector = XPath("//header/h1")

        _bloat_topics = {
            "newsticker",
            "SpiO",
            "Sport",
            "Sport im Osten",
            "kulturnachrichten",
            "kulturarena",
            "Thüringen",
            "Sachsen",
            "Sachsen-Anhalt",
            "Anhalt",
        }

        @function(priority=1)
        def insert_quote_punctuation(self) -> None:
            blockquote_nodes = self._blockquote_text_content_selector(self.precomputed.doc)
            for blockquote_node in blockquote_nodes:
                blockquote_node.text = f"«{blockquote_node.text}.» - "


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
            return generic_topic_parsing(self.precomputed.meta.get("keywords"), result_filter=self._bloat_topics)

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(
                self.precomputed.ld.xpath_search("//NewsArticle/author"), split_on=[", ", " und "]
            )

        @attribute
        def title(self) -> Optional[str]:
            return strip_nodes_to_text(self._headline_selector(self.precomputed.doc))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//article"),
                image_selector=XPath("//article//img[not(ancestor::div[contains(@class, 'teaser')])]"),
                caption_selector=XPath(
                    "./ancestor::div[contains(@class, 'contentimage')]//span[@class='caption small']"
                ),
                lower_boundary_selector=XPath("//nav[@class='sharebox']"),
                relative_urls=True,
            )
