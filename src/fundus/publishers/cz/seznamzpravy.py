import datetime
import re
from typing import List, Optional, Pattern

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    apply_substitution_pattern_over_list,
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class SeznamZpravyParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            "//div[contains(@class,'mol-rich-content--for-article')]/div[contains(@class,'speakable')]/p"
        )
        _summary_selector = XPath("//div/p[contains(@class, 'speakable') and @*[contains(., 'ogm-article-perex')]]")
        _subheadline_selector = XPath("//div[contains(@class,'mol-rich-content--for-article')]/h2")
        _author_substitution_pattern: Pattern[str] = re.compile(r"Seznam Zprávy")

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
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def authors(self) -> List[str]:
            return apply_substitution_pattern_over_list(
                generic_author_parsing(self.precomputed.ld.bf_search("author")),
                pattern=self._author_substitution_pattern,
                replacement="",
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//figure//img[not(ancestor::div[contains(@class, 'mol-post-card__body')])]"),
                author_selector=XPath("./ancestor::figure//span[@*[contains(., 'atm-media-item-image-caption')]]"),
                relative_urls=True,
            )
