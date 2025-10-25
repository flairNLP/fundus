import datetime
import re
from typing import List, Optional, Pattern

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.data import Image
from fundus.parser.utility import (
    apply_substitution_pattern_over_list,
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class FunkeParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2025, 8, 24)

        _author_substitution_pattern: Pattern[str] = re.compile(r"FUNKE Mediengruppe|.*dpa(:|-infocom).*|^red$")
        _paragraph_selector = XPath(
            "//div[@class='article-body']//p[not(not(text()) or @rel='author' or em[@class='print'] or @class)]"
        )
        _summary_selector = XPath("//div[@class='article-body']/p[contains(@class, 'font-sans')]")
        _subheadline_selector = XPath(
            "//div[@class='article-body']//h3[not("
            "contains(text(), 'Alle Artikel der Serie')"
            " or contains(text(), 'Mehr zum Thema')"
            " or contains(text(), 'weitere Videos')"
            " or contains(text(), 'Auch interessant')"
            " or contains(text(), 'Weitere News')"
            " or @class)]"
        )
        _topics_selector = XPath("//div[@class='not-prose  mb-4 mx-5 font-sans']/ul/li")
        _image_selector = XPath("//img[not(contains(@class, 'rounded-full'))]")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            if topics := generic_topic_parsing(self.precomputed.meta.get("news_keywords")):
                return topics
            else:
                pass
            return [
                re.sub(r"\s*–.+", "", node.text_content()).strip()
                for node in self._topics_selector(self.precomputed.doc)
            ]

        @attribute
        def authors(self) -> List[str]:
            return apply_substitution_pattern_over_list(
                generic_author_parsing(self.precomputed.ld.bf_search("author")), self._author_substitution_pattern
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=self._image_selector,
                author_selector=re.compile(r"©(?P<credits>.*)"),
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()

        _paragraph_selector = XPath(
            "//div[contains(@class,'article-body')]"
            "/p[contains(@class,'expressive-copy-lg-body') and not(contains(text(), '>>')) and string-length(text()) > 10]|"
            "//div[contains(@class,'article-body')]//ul/li[string-length(text())>10 and not(a or article)]"
        )
        _subheadline_selector = XPath(
            "//div[contains(@class,'article-body')]//h3[not("
            "contains(text(), 'Alle Artikel der Serie')"
            " or contains(text(), 'Mehr zum Thema')"
            " or contains(text(), 'weitere Videos')"
            " or contains(text(), 'Auch interessant')"
            " or contains(text(), 'Weitere News')"
            " or not(contains(@class, 'expressive-heading-xl'))"
            " or following-sibling::*[1][self::ul])]"
        )
        _summary_selector = XPath("//div[contains(@class, 'expressive-copy-lg')]")
        _image_selector = XPath(
            "//img[contains(@class, 'lg:aspect-[16/9]') or not(contains(@class, 'aspect-[1/1]'))] | //figure/picture"
        )
