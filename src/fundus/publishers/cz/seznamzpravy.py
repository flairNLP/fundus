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
        VALID_UNTIL = datetime.date(2025, 8, 1)  # This date is an estimate, since our logs don't date
        # back far enough to accurately determine and it is unclear from archives.

        _paragraph_selector = XPath(
            "//div[contains(@class,'mol-rich-content--for-article')]/div[contains(@class,'speakable')]/p"
        )
        _summary_selector = XPath("//div/p[contains(@class, 'speakable') and @*[contains(., 'ogm-article-perex')]]")
        _subheadline_selector = XPath("//div[contains(@class,'mol-rich-content--for-article')]/h2")
        _author_substitution_pattern: Pattern[str] = re.compile(r"Seznam Zprávy")

        _bloat_topics = ["BLUE", "RED"]

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
            return [
                topic
                for topic in generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))
                if topic not in self._bloat_topics
            ]

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

    class V1_1(V1):
        VALID_UNTIL = datetime.date(2025, 11, 24)

        _paragraph_selector = XPath("//div[@class='h_f7 h_bZ h_bZ']/div/p/span[@class='atm-text-decorator' and text()]")
        _subheadline_selector = XPath(
            "//div[@class='h_f7 h_bZ h_bZ']/div/p/span[@class='atm-text-decorator']/span | "
            "//div[@class='h_f7 h_bZ h_bZ']/h2"
        )

    class V1_2(V1_1):
        VALID_UNTIL = datetime.date.today()

        _paragraph_selector = XPath("//article[@role='article'] //div[contains(@class, 'speakable')] //p")
        _subheadline_selector = XPath("//article[@role='article'] //h2[contains(@class, 'speakable')]")
