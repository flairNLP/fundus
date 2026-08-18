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
        _summary_selector = XPath("//article//p[@class='detail__excerpt wp-block-paragraph']")
        _paragraph_selector = XPath(
            r"//article//div[contains(@class, 'entry-content')]//p[not(re:test(string(.), '^(– |Redigatur|Redaktion|Mitarbeit|Faktencheck|Grafiken|\*\*\*)')) and (not(b or @class or @style) or @class='wp-block-paragraph')] |"
            "//article//div[contains(@class, 'entry-content')]//li",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _subheadline_selector = XPath(
            "//article//div[contains(@class, 'entry-content')]//*[(self::h2 or self::h3) or (self::p and b)]"
        )

        _bloat_topics = {"Featured-auf-Startseite"}

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
            return generic_author_parsing(self.precomputed.ld.xpath_search("//NewsArticle//author"))

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
                author_selector=re.compile(r"(?i)(foto|quelle):(?P<credits>.+)$"),
            )
