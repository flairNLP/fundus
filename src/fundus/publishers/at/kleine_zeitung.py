import datetime
import re
from typing import List, Optional, Pattern, Union

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class KleineZeitungParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2026, 7, 24)

        _paragraph_selector = XPath("//div[@class='w-full prose']/p")
        _subheadline_selector = XPath("//div[@class='w-full prose']/h2")
        _summary_selector = XPath("//div[contains(@class, 'article-lead')]")

        _image_author_selector: Union[Pattern[str], XPath] = re.compile(r"©(?P<credits>.*?)$")

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
            return self.precomputed.ld.xpath_search("NewsArticle/headline", scalar=True)

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                image_selector=XPath("//figure//img|//div[contains(@class, 'not-prose') or @class=' mb-0']/img"),
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//h1"),
                caption_selector=XPath(
                    "./ancestor::figure//*[self::figcaption or contains(@class, 'md:hidden')]|"
                    "./ancestor::div[contains(@class, 'not-prose') or @class=' mb-0']//small"
                ),
                author_selector=self._image_author_selector,
            )

    class V1_1(V1):
        _paragraph_selector = XPath("//div[contains(@class,'prose')]/p")
        _subheadline_selector = XPath("//div[contains(@class,'prose')]/h2")
        _summary_selector = XPath("//p[@class='klz-text-article-lead']")

        _image_author_selector = XPath("./ancestor::figure//small")
