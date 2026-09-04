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
        # credit labels CORRECTIV sets at the foot of an article
        _paragraph_bloat_sentence_beginnings = [
            "Text and research",
            "Text & Recherche",
            "Editing",
            "Fact-checking",
            "Data work",
            "Design",
            "Redigat",  # covers both "Redigatur" and "Redigat und Faktencheck"
            "Redaktion",
            "Mitarbeit",
            "Faktencheck",
            "Grafiken",
        ]

        # paragraphs matching one of these carry credits, bylines or separators instead of body text
        _paragraph_bloat_patterns = [
            r"– ",
            r"\*\*\*",
            r"_ _",  # underscore separator rule, e.g. "_ _ _ _ _ _ _ _"
            r"von ",  # byline, e.g. "von Gesa Steeger und Annika Joeres" (lowercase; prose starts capitalized)
            r"\d{1,2}\. \w+ \d{4}$",  # standalone dateline, e.g. "19. August 2026"
            *_paragraph_bloat_sentence_beginnings,
        ]
        _bloat_pattern = "|".join(_paragraph_bloat_patterns)
        _is_bloat_paragraph = f"re:test(string(.), '^({_bloat_pattern})')"

        # a paragraph that is nothing but a bold run is a subheadline; nothing but an italic run
        # is an editorial note or a credit line ("Illustration: ..."). count(*) keeps this off
        # body prose that merely italicizes a word or two.
        _is_bold_only = "b and not(text())"
        _is_italic_only = "i and count(*) = 1 and not(text())"

        # markup variants CORRECTIV uses for body paragraphs; anything else is layout or credits
        _is_body_paragraph = " or ".join(
            [
                f"not(({_is_bold_only}) or ({_is_italic_only}) or @class or @style)",
                "@class = 'wp-block-paragraph'",
                "contains(@class, 'text-base')",
            ]
        )

        # the body lives in 'entry-content'; some articles wrap additional paragraphs in a '-container'
        _entry_content = "//article//div[contains(@class, 'entry-content')]"
        _paragraph_container = "//article//div[contains(@class, 'entry-content') or contains(@class, '-container')]"

        _summary_selector = XPath("//article//p[@class='detail__excerpt wp-block-paragraph']")
        _paragraph_selector = XPath(
            f"{_paragraph_container}/p"
            f"[not({_is_bloat_paragraph}) and ({_is_body_paragraph}) and string-length(normalize-space(.)) > 1]"
            f" | {_entry_content}//*[self::li or self::blockquote]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _subheadline_selector = XPath(f"{_entry_content}/*[(self::h2 or self::h3) or (self::p and {_is_bold_only})]")

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
            re.compile(r"(?i)(?:(?<=\. )|\s*\(\s*)(?P<credits>(?:[^().:]|\.com)*[/|](?:[^().:]|\.com)*?)\)?\.?\s*$"),
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
