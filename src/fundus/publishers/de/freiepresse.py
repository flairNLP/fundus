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


class FreiePresseParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2024, 8, 4)
        _summary_selector = CSSSelector("#artikel-content > p.bold")
        _paragraph_selector = XPath(
            "//*[@id='artikel-content']//p[not(ancestor::div[@class='pw-layer'] or @class='bold')]"
        )
        _subheadline_selector = CSSSelector("#artikel-content h2")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            if not (authors := self.precomputed.ld.xpath_search("NewsArticle/author")):
                return []
            else:
                return generic_author_parsing(
                    [author for author in authors if not author == "Chemnitzer Verlag und Druck GmbH & Co. KG"]
                )

        @attribute
        def title(self) -> Optional[str]:
            if title := self.precomputed.meta.get("og:title"):
                return re.sub(r"\s*\|.*", "", title)
            return None

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.bf_search("keywords"), delimiter="/")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath(
                    "((//div[contains(@class,'wrapImg')]//picture)[1])//img | //img[@class='media-image']"
                ),
                lower_boundary_selector=XPath("//div[@class='section-topic']"),
                caption_selector=XPath("./ancestor::li[@class='img gallery-item']//span[@class='img-info']"),
                author_selector=re.compile(r"(?i)bild:(?P<credits>.*)"),
                relative_urls=True,
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()
        _paragraph_selector = CSSSelector("#artikel-content p:not(.bold)")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath(
                    "//div[@class='detail-img__image-wrapper detail-img__image-wrapper--gradient']//img"
                ),
                lower_boundary_selector=CSSSelector("a.article__copyright"),
                caption_selector=XPath(
                    "./ancestor::div[@class='detail-img']//div[@class='detail-img__description no-transition']/div/text()"
                ),
                author_selector=re.compile(r"(?i)bild:(?P<credits>.*)"),
                relative_urls=True,
            )
