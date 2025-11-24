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
    strip_nodes_to_text,
)


class NTVTRParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2025, 11, 4)

        _paragraph_selector = XPath("//div[@class='content-news-tag-selector']/p")
        _summary_selector = XPath("//h2[@class='category-detail-sub-title']")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("dmp:tags"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("articleAuthor"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=CSSSelector("article, div.category-detail-inner"),
                lower_boundary_selector=CSSSelector("div.social:last-of-type"),
                image_selector=XPath("//div[contains(@class, 'img-wrapper')]//img | //picture /img"),
            )

    class V2(BaseParser):
        VALID_UNTIL = datetime.date.today()

        _paragraph_selector = XPath("//div[contains(@class, 'content')]/p[text()]")
        _summary_selector = XPath("//div[contains(@class, 'info-text-card')]//h2")
        _subheadline_selector = XPath(
            "//div[contains(@class, 'content')]/p[not(text()) and strong] | //div[@data-imageindex]//h2"
        )

        _topics_selector = XPath("(//ul[contains(@class, 'text-[#3D619B]')])[1]/li")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            if title := self.precomputed.meta.get("og:title"):
                return title.replace("| NTV Haber", "").strip()
            return None

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(
                strip_nodes_to_text(self._topics_selector(self.precomputed.doc), join_on=","),
                substitution_pattern=re.compile(r"-\s*$"),
                delimiter=",",
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("articleAuthor"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=CSSSelector("h1"),
                lower_boundary_selector=XPath("(//img[@alt='Google Play'])[1]"),
                image_selector=XPath(
                    "//div[@property='articleBody']//img[not(@fetchpriority='auto') or @height > 300]"
                ),
                caption_selector=XPath("./ancestor::div[contains(@class,'relative') and p]/p"),
                author_selector=XPath("./ancestor::div[contains(@class,'relative') and (picture or img)]/div"),
            )
