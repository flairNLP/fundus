import datetime
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


class JungeWeltParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2026, 4, 24)

        _paragraph_selector = XPath(
            "//div[@class = 'row']/div[contains(@class, 'col') and not(@class = 'col-md-8 mx-auto mt-4 bg-light')]/p"
        )
        _summary_selector: XPath = CSSSelector(".teaser.lead")
        _subheadline_selector = XPath("//div[@class = 'row']/div[contains(@class,'col')]/h3")
        _free_access_selector = XPath("//h1[text()='Sie sind nun eingeloggt.']|//p[@class='m-1']")

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
            return generic_author_parsing(self.precomputed.meta.get("Author"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def free_access(self) -> bool:
            return not bool(self._free_access_selector(self.precomputed.doc))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                caption_selector=XPath("./ancestor::figure//div[contains(@class, 'caption')]"),
                relative_urls=True,
            )

    class V1_1(V1):
        _paragraph_selector = XPath(
            "//div[div[@id='article-meta-footer']] //div[contains(@class, 'content')]//p[not(strong) or text()]"
        )
        _summary_selector = XPath("//article/h2 | //div[contains(@class, 'content')]/p[position()=1 and strong]")
        _subheadline_selector = XPath(
            "//div[contains(@class, 'content')]/h3 | //div[contains(@class, 'content')]/p[position()>1 and strong]"
        )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                image_selector=XPath("//article//div[contains(@class, 'mx-auto')]/img"),
                paragraph_selector=self._paragraph_selector,
                caption_selector=XPath(
                    "./ancestor::div[contains(@class, 'mx-auto')]//div[contains(@class, 'text-base/6')]"
                ),
                author_selector=XPath("./ancestor::div[contains(@class, 'mx-auto')]//span"),
                relative_urls=True,
            )
