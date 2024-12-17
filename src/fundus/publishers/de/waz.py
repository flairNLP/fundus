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


class WAZParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2024, 2, 21)
        _paragraph_selector: XPath = CSSSelector(".article__body > p")
        _summary_selector: XPath = CSSSelector(".article__header__intro__text")
        _subheadline_selector: XPath = CSSSelector(".article__body > h3")
        _topics_selector = XPath("//div[@class='not-prose  mb-4 mx-5 font-sans']/ul/li")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def topics(self) -> List[str]:
            authors = generic_author_parsing(self.precomputed.meta.get("author"))
            if topics := generic_topic_parsing(self.precomputed.meta.get("keywords")):
                return [topic for topic in topics if topic not in authors]
            else:
                pass
            return [
                re.sub(r"\s*:.+", "", node.text_content()).strip()
                for node in self._topics_selector(self.precomputed.doc)
            ]

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                lower_boundary_selector=XPath("//a[@href='/' and contains(text(), 'Startseite')]"),
                caption_selector=XPath("(./ancestor::figure//figcaption//span)[1]"),
                author_selector=XPath("(./ancestor::figure//figcaption//span)[2]"),
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()

        _paragraph_selector = XPath(
            "//div[@class='article-body'] /p[position()>1 and not(@rel='author' or re:test(string(), '^>>.*[+]{3}'))]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _summary_selector = XPath("//div[@class='article-body'] /p[position()=1]")
        _subheadline_selector = XPath("//div[@class='article-body'] / h3[not(text()='Auch interessant')]")
