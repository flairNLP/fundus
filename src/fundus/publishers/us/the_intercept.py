from datetime import date, datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    image_extraction,
)


class TheInterceptParser(ParserProxy):
    class V1(BaseParser):
        # this date isn't exact nor confirmed, because TheIntercept isn't included an CC-NEWS and the
        # Publisher Coverage action didn't capture the layout change.
        VALID_UNTIL = date(2024, 2, 1)
        _summary_selector: XPath = CSSSelector("h2.Post-excerpt")
        _paragraph_selector: XPath = CSSSelector(
            "div.PostContent > div > p:not(p.caption):not(p.PhotoGrid-description)"
        )
        _subheadline_selector: XPath = CSSSelector("div.PostContent > div > h2")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                # The Intercept uses `p` tags for the article's paragraphs, image captions and photo grid descriptions.
                # Since we are only interested in the article's paragraphs,
                # we exclude the other elements from the paragraph selector.
                # Example article: https://theintercept.com/2023/04/01/israel-palestine-apartheid-settlements/
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.xpath_search("NewsArticle/author"))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.ld.xpath_search("NewsArticle/datePublished", scalar=True))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.xpath_search("NewsArticle/headline", scalar=True)

        @attribute
        def topics(self) -> List[str]:
            # The Intercept specifies the article's topics, including other metadata,
            # inside the "keywords" linked data indicated by a "Subject: " prefix.
            # Example keywords: ["Day: Saturday", ..., "Subject: World", ...]
            keywords: List[str] = self.precomputed.ld.xpath_search("NewsArticle/keywords")
            return [keyword[9:] for keyword in keywords if keyword.startswith("Subject: ")]

    class V1_1(V1):
        VALID_UNTIL = date.today()
        _summary_selector = XPath(
            "//p[@class='post__excerpt'] | //h2[preceding-sibling::h1[contains(@class, 'post__title')]]"
        )
        _paragraph_selector = CSSSelector("div.entry-content > div.entry-content__content > p, blockquote > p")
        _subheadline_selector = CSSSelector("div.entry-content > div.entry-content__content > h2")

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath(
                    "//img[(string-length(@alt) > 0 and not(contains(@class, 'attachment') or contains(@class, ':hidden'))) or @loading='eager']|//figure//img"
                ),
                caption_selector=XPath(
                    "(./parent::article//div[contains(@class, 'image__caption')]/span[not(@class)])[1]|"
                    "./ancestor::figure//figcaption/span[@class='photo__caption']"
                ),
                author_selector=XPath(
                    "(./parent::article//div[contains(@class, 'image__caption')]/span)[last()]|"
                    "./ancestor::figure//figcaption/span[@class='photo__credit']"
                ),
            )
