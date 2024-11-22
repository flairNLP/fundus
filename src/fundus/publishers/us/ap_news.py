import datetime
import re
from typing import List, Optional, Pattern

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
    normalize_whitespace,
)


class APNewsParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2023, 7, 10)
        _author_selector: XPath = XPath(f"{CSSSelector('div.CardHeadline').path}/span/span[1]")
        _subheadline_selector = XPath("//div[@data-key = 'article']/h2[not(text()='___')]")
        _paragraph_selector = XPath("//div[@data-key = 'article']/p")

        _topic_bloat_pattern: Pattern[str] = re.compile(r"state wire| news|^.{1}$", flags=re.IGNORECASE)

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            # AP News does not have all the article's authors listed in the linked data.
            # Therefore, we try to parse the article's authors from the document.
            try:
                # Example: "By AUTHOR1, AUTHOR2 and AUTHOR3"
                author_string: str = normalize_whitespace(self._author_selector(self.precomputed.doc)[0].text_content())
                author_string = re.sub(r"^By ", "", author_string)
            except IndexError:
                # Fallback to the generic author parsing from the linked data.
                return generic_author_parsing(self.precomputed.ld.xpath_search("NewsArticle/author"))

            return generic_author_parsing(author_string)

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.xpath_search("NewsArticle/datePublished", scalar=True))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.xpath_search("NewsArticle/headline", scalar=True)

        @attribute
        def topics(self) -> List[str]:
            return [
                topic
                for topic in generic_topic_parsing(self.precomputed.meta.get("keywords"))
                if not re.search(self._topic_bloat_pattern, topic)
            ]

        # unfortunately we would need to render the site first before parsing images for this version

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()

        _author_selector = CSSSelector("div.Page-authors")
        _subheadline_selector = XPath("//div[contains(@class, 'RichTextStoryBody')] /h2[not(text()='___')]")
        _paragraph_selector = XPath(
            "//div[contains(@class, 'RichTextStoryBody')] "
            "/p[not(preceding-sibling::*[1][self::h2 and text()='___'])]"
            # only p-elements not directly following h2 elements with text() = '___'
        )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//*[self::figure or @class='CarouselSlide']//img"),
                caption_selector=XPath(
                    "./ancestor::figure//figcaption | "
                    "./ancestor::div[@class='CarouselSlide']//span[@class='CarouselSlide-infoDescription']"
                ),
                upper_boundary_selector=XPath("//div[@class='Page-content' or @class='Body']"),
                lower_boundary_selector=CSSSelector("footer.Page-footer"),
                author_selector=re.compile(r"\s*\((?P<credits>.*)\)$"),
            )
