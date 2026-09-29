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
    generic_topic_parsing,
    image_extraction,
)


class SportSchauParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2025, 10, 13)

        _summary_selector: XPath = CSSSelector(
            "p[class='textabsatz columns twelve  m-ten  m-offset-one l-eight l-offset-two'] > strong"
        )
        _paragraph_selector: XPath = CSSSelector("article >p.textabsatz:not(p.textabsatz:nth-of-type(1))")
        _subheadline_selector: XPath = CSSSelector("article >h2")

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
            return generic_author_parsing(self.precomputed.meta.get("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(
                self.precomputed.meta.get(
                    "date",
                )
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//article//picture[not(contains(@class,'--list'))]//img"),
                lower_boundary_selector=XPath("//div[contains(@class, 'back-to-top')]"),
                alt_selector=XPath("./@title"),
                author_selector=re.compile(r"\|(?P<credits>.+)"),
                caption_selector=XPath(
                    "./ancestor::div[contains(@class, 'absatzbild ')]/div[@class='absatzbild__info']"
                ),
                size_pattern=re.compile(r"/[\dx]+-(?P<width>[0-9]+)/"),
            )

    class V1_1(V1):
        _summary_selector = CSSSelector("p.article-head__shorttext > strong")
        _paragraph_selector = XPath(
            r"""
            //article/p[contains(@class, 'textabsatz') and not(re:test(normalize-space(.),
                '^(Sendung:|Unsere Quellen:|Quelle:|Erstveröffentlichung:|Über dieses Thema|Das ist die Europäische Perspektive|Tabellenführung und Abstiegskampf|"Hier ist Bayern")'))]
            | //article/div//blockquote[contains(@class, 'zitat')]
            | //article/div[not(preceding-sibling::*[1][starts-with(normalize-space(.), 'Unsere Quellen')])]
                /ul[contains(@class, 'bulletpoint-list')]
                /li[not(a[starts-with(@href, '#')] or starts-with(normalize-space(.), 'An dieser Stelle befindet sich externer Inhalt'))]
            """,
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _subheadline_selector = XPath(
            r"""
            //article/h2[not(
                starts-with(normalize-space(.), 'Unsere Quellen')
                or starts-with(normalize-space(.), 'Im Video:')
                or following-sibling::*[1][.//*[contains(@class, 'teaser-absatz') or contains(@class, 'infobox')]]
            )]
            """
        )
