import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class CNBCParser(ParserProxy):
    class V1(BaseParser):
        _subheadline_selector: CSSSelector = CSSSelector("div[data-module = 'ArticleBody'] > h2")
        _paragraph_selector: XPath = XPath("//div[@data-module='ArticleBody'] / div[@class='group'] / p[text()]")
        _key_points_selector: CSSSelector = CSSSelector("div.RenderKeyPoints-list li")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            body: ArticleBody = extract_article_body_with_selector(
                self.precomputed.doc,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )
            return body

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.xpath_search("NewsArticle/author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.xpath_search("NewsArticle/datePublished", scalar=True))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.xpath_search("NewsArticle/headline", scalar=True)

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute(validate=False)
        def key_points(self) -> List[str]:
            return [key_point.text_content() for key_point in self._key_points_selector(self.precomputed.doc)]

        """
        CNBC uses unconventional image loading, which is not supported at the time
        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//h1[@class='ArticleHeader-headline']"),
                image_selector=XPath("//div[@class='InlineImage-wrapper']//img"),
                caption_selector=XPath("./ancestor::div[@class='InlineImage-wrapper']//div[@class='InlineImage-imageEmbedCaption']"),
                author_selector=XPath(
                    "./ancestor::div[@class='InlineImage-wrapper']//div[@class='InlineImage-imageEmbedCredit']")
            )
        """
