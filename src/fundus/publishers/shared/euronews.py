from datetime import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import (
    ArticleBody,
    BaseParser,
    Image,
    ParserProxy,
    attribute,
    utility,
)
from fundus.parser.utility import image_extraction


class EuronewsParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("p.c-article-summary")
        _subheadline_selector = CSSSelector("div.c-article-content > h2")
        _paragraph_selector = CSSSelector("div.c-article-content > p")

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            article_body = utility.extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )
            return article_body

        @attribute
        def authors(self) -> List[str]:
            author_string = self.precomputed.ld.xpath_search("NewsArticle/author/name")
            return utility.generic_author_parsing(author_string)

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            date_string = self.precomputed.meta.get("date.available")
            return utility.generic_date_parsing(date_string)

        @attribute
        def topics(self) -> List[str]:
            keyword_string = self.precomputed.meta.get("keywords")
            return utility.generic_topic_parsing(keyword_string)

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath(
                    "//img[contains(@class, 'c-article-media__img')" " or contains(@class, 'widgetImage__image')]"
                ),
                caption_selector=XPath(
                    "./ancestor::div[contains(@class, 'c-article-image-video')]"
                    "//div[contains(@class, 'c-article-caption__content')]|"
                    "./ancestor::figure//span[@class='widget__captionText']"
                ),
                author_selector=XPath(
                    "./ancestor::div[contains(@class, 'c-article-image-video')]"
                    "//div[contains(@class, 'c-article-image-copyright')]|"
                    "./ancestor::figure//span[@class='widget__captionCredit']"
                ),
            )
