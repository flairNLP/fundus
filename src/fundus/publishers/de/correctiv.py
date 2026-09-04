import datetime
import re
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


class CorrectivParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2026, 8, 10)

        _summary_selector = XPath("//p[@class='detail__excerpt']")
        _subheadline_selector = XPath("//div[@class='detail__content']/*[self::h3 or self::h2]")
        _paragraph_selector = XPath("//div[@class='detail__content']/p[string-length(text())>1 or span]")

        _author_selector = XPath("//p[@class='detail__authors']/a")

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
            return generic_author_parsing(generic_nodes_to_text(self._author_selector(self.precomputed.doc)))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.xpath_search("//NewsArticle/headline", scalar=True)

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//figure[@id]/img | //figure[@class='figure']/picture/img"),
                author_selector=[
                    re.compile(
                        r"(?i)(?<=\. )((foto|credit image|bild|image|symbolbild):|©)?\s*(?P<credits>([^.:]|CORRECTIV\.|.com)+?)([.])?$"
                    ),
                    re.compile(r"\((.+:)?(?P<credits>[^):]+?)\)$"),
                    re.compile(r"/(?P<credits>.+)$"),
                ],
            )

    class V2(BaseParser):
        _paragraph_bloat_sentence_beginnings = [
            "Text and research",
            "Editing",
            "Fact-checking",
            "Data work",
            "Design",
            "Redigatur",
            "Redaktion",
            "Mitarbeit",
            "Faktencheck",
            "Grafiken",
        ]

        _summary_selector = XPath("//article//p[@class='detail__excerpt wp-block-paragraph']")
        _paragraph_selector = XPath(
            r"//article//div[contains(@class, 'entry-content') or contains(@class,'-container')]/p"
            rf"[not(re:test(string(.), '^(– |{'|'.join(_paragraph_bloat_sentence_beginnings)}|\*\*\*)')) "
            r"and ("
            r"not((b and not(text())) or @class or @style) "
            r"or @class='wp-block-paragraph' "
            r"or contains(@class, 'text-base')"
            r") and string-length(text())>1"
            r"] |"
            "//article//div[contains(@class, 'entry-content')]//*[self::li or self::blockquote]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _subheadline_selector = XPath(
            "//article//div[contains(@class, 'entry-content')]/*[(self::h2 or self::h3) or (self::p and b and not(text()))]"
        )

        # keywords CORRECTIV uses to introduce image credits within a caption
        _credit_keywords = (
            r"(?:(?:f|ph)otos?(?:-scan)?|bild(?:er)?|symbol(?:bild|foto)|collagen?|montagen?|"
            r"quellen?|screenshots?|grafiken?|illustrationen?|credits?|wasserzeichen)"
        )
        _author_selector = [
            # credits given in parentheses, e.g. "... (Foto: picture alliance/dpa | Hendrik Schmidt)"
            re.compile(rf"(?i)\s*\(\s*{_credit_keywords}\s*:\s*(?P<credits>[^()]+?)\)?\.?\s*$"),
            # credits introduced by a keyword, e.g. "... Collage: Ivo Mayr / CORRECTIV, Fotos: picture alliance"
            re.compile(rf"(?i)\s*[/;,]?\s*\b{_credit_keywords}\s*:\s*(?P<credits>.+?)\.?\s*$"),
            # credits introduced by a copyright sign or a dash, e.g. "... Chemnitz. \u00a9Ralf Jerke"
            re.compile(r"(?i)(?<=\.)\s*(?:\u00a9|[\u0096\u2013\u2014-])\s*(?P<credits>(?:[^.:]|\.com)+?)\.?$"),
            # bare agency credits trailing a sentence, e.g. "... Cavallo. picture alliance/dpa | Martin Meissner"
            re.compile(
                r"(?i)(?:(?<=\. )|\s*\(\s*)(?P<credits>(?:[^().:]|\.com)*[/|](?:[^().:]|\.com)*?)\)?\.?\s*$"
            ),
        ]

        # inline image credits are rendered as a <span> following an <img> within a paragraph
        _caption_filter = XPath("self::span[preceding-sibling::img]")

        _bloat_topics = {"Featured-auf-Startseite", "Related Articles am Ende"}

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
                tag_filter=self._caption_filter,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.xpath_search("//NewsArticle//author|//Article//author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.bf_search("keywords"), result_filter=self._bloat_topics)

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                author_selector=self._author_selector,
                image_selector=XPath("//figure[@id]/img | //figure[@class='figure']/picture/img"),
            )
