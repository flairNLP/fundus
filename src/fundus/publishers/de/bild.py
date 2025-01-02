import datetime
import re
from typing import List, Optional

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


class BildParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[@class = 'article-body']/p[position() > 1]")
        _summary_selector = XPath("//div[@class = 'article-body']/p[1]")
        _subheadline_selector = XPath("//div[@data-key = 'article']/h2")

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
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute
        def free_access(self) -> bool:
            if (url := self.precomputed.meta.get("og:url")) is not None:
                return re.search(r"/bild-plus/", url) is None
            else:
                return True

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//figure//img[not(contains(@class, 'teaser') or contains(@class, 'author'))]"),
                caption_selector=XPath("./ancestor::figure//p[@class='fig__caption__text']"),
                author_selector=XPath("./ancestor::figure//div[@class='fig__caption__meta']"),
            )
