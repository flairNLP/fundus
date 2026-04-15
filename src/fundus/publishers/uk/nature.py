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


class NatureParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2026, 2, 1)  # This date is the best guess
        _summary_selector: XPath = CSSSelector("div.c-article-abstract p, p.c-article-abstract")

        _paragraph_selector = XPath(
            "//div[@data-test='access-teaser']//p"
            "["
            "  not(ancestor::*[@data-label='Related' or contains(@class, 'recommended')])"
            "  and not(contains(@class, 'recommended__title'))"
            "  and not(ancestor::figure)"
            "  and not(ancestor::figcaption)"
            "  and not(ancestor::a)"
            "]"
        )

        _subheadline_selector = XPath(
            "//div[@data-test='access-teaser']//h2" "[not(ancestor::article[contains(@class, 'recommended')])]"
        )

        _lower_boundary_selector = XPath(
            "(//*[(@class='app-access-wall') or "
            "contains(@class, 'c-related-articles') or "
            "(self::article and contains(@class, 'related'))])[1]"
        )
        _caption_selector = XPath("./ancestor::figure//figcaption")
        _author_pattern = re.compile(r"(?i)\s*(credit|source|illustration|analysis by):?\s+(?P<credits>.*)")

        _bloat_topics = {"multidisciplinary", "Science", "Humanities and Social Sciences"}

        _paywall_selector = XPath("//div[@class='app-access-wall__container']")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.bf_search("keywords"), result_filter=self._bloat_topics)

        @attribute
        def free_access(self) -> bool:
            return not bool(self._paywall_selector(self.precomputed.doc))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                relative_urls=True,
                caption_selector=self._caption_selector,
                author_selector=self._author_pattern,
                lower_boundary_selector=self._lower_boundary_selector,
            )

    class V1_1(V1):
        _paragraph_selector = XPath(
            "//div[@data-test='main-content' or contains(@class,'main-content')]//p"
            "["
            "  not(ancestor::*[@data-label='Related' or contains(@class, 'recommended')])"
            "  and not(contains(@class, 'recommended__title'))"
            "  and not(ancestor::figure)"
            "  and not(ancestor::figcaption)"
            "  and not(ancestor::a)"
            "  and not(contains(@class, 'app-access-wall'))"
            "  and text()"
            "] |"
            "//div[@class='c-article-body']/section//p |"
            "//p[@class='article__teaser']"
        )
        _summary_selector = XPath("//div[@class='c-article-teaser-text']")
        _subheadline_selector = XPath(
            "//div[@data-test='main-content' or contains(@class,'main-content')]"
            "//h2"
            "["
            "not(ancestor::article[contains(@class, 'recommended')])"
            "  and not(contains(@class, 'app-access-wall'))"
            "  and not(@id='access-options')"
            "] |"
            "//div[@class='c-article-body']/section//h2"
        )

        _lower_boundary_selector = XPath("(//aside)[2]")
        _paywall_selector = XPath("//div[contains(@class, 'buybox')]")
