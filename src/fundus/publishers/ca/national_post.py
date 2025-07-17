import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.data import Image
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)
from fundus.scraping.filter import regex_filter


class NationalPostParser(ParserProxy):
    class V1(BaseParser):
        # Note: this date is approximate. The actual date lies between 2025-04-06 and 2025-04-15. This is due to
        # National Posts exclusion from archive.org and problems with the publisher coverage.
        VALID_UNTIL = datetime.date(2025, 4, 15)

        _summary_selector = CSSSelector("article p.article-subtitle")
        _subheadline_selector = XPath(
            "//section[@class='article-content__content-group article-content__content-group--story']/p/strong | "
            "//section[@class='article-content__content-group article-content__content-group--story']/h3"
        )
        _paragraph_selector = XPath(
            "//section[@class='article-content__content-group article-content__content-group--story']/p[text()]"
        )

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
            preliminary_topics = self.precomputed.ld.bf_search("keywords")
            filter_list = ["Curated", "News", "Newsroom daily", "story", "Canada", "World", "nationalpost.com"]
            topic_filter = regex_filter(
                r"([0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}|NLP Entity Tokens|NLP Category|NP Comment|Category:)"
            )
            filtered_topics = [
                topic for topic in preliminary_topics if not topic_filter(topic) and topic not in filter_list
            ]
            return generic_topic_parsing(filtered_topics)

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//div[@class='article-header__detail']/figure"),
                lower_boundary_selector=CSSSelector("section.article-delimiter"),
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()

        _paragraph_selector = XPath(
            "//div[@class='story-v2-content-element-inline']/"
            "p[text() and not(@data-async) and not(text()='National Post')]"
        )
        _subheadline_selector = XPath(
            "//div[@class='story-v2-content-element-inline']/h3 |"
            "//div[@class='story-v2-content-element-inline']/p/strong"
        )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("(//div[@class='story-v2-block story-v2-article-container'])[1]"),
                lower_boundary_selector=XPath("//section[@class='article-content__share-group']"),
                caption_selector=XPath("./ancestor::figure/figcaption/span[@class='caption']"),
                author_selector=XPath("./ancestor::figure/figcaption/span[@class='credit' or @class='distributor']"),
            )
