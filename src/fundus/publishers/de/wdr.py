import datetime
import re
from typing import List, Optional

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class WDRParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            "//article//p[starts-with(@class,'text') and not(position()=last())  and not(contains(text(), 'Quelle'))]"
        )
        _summary_selector = XPath("//article//p[starts-with(@class,'einleitung')]")
        _subheadline_selector = XPath("//article//h2[@class='subtitle small']")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("Author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("Keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath(
                    "//article//picture[not(@data-resp-img-id='LinklistenteaserImageSectionZModA')]//img[@class='img']"
                ),
                upper_boundary_selector=XPath("//div[@class='segment']"),
                lower_boundary_selector=XPath("//div[@class='shareCon']"),
                alt_selector=XPath("./@title"),
                author_selector=re.compile(r"(?i)\|\s*bildquelle:(?P<credits>.+)"),
                relative_urls=True,
                caption_selector=XPath("./ancestor::div[@class='media mediaA']//p[@class='infotext']"),
            )
