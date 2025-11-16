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
    strip_nodes_to_text,
)


class ZDFParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2025, 8, 1)  # This date could not be verified exactly

        _paragraph_selector = XPath("//div[contains(@class,'r1nj4qn5')]")
        _summary_selector = CSSSelector("p.c1bdz7f4")
        _subheadlines_selector = CSSSelector("h2.hhhtovw")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadlines_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath(
                    "//picture//img[not(contains(@class, 'error') or contains(@src, 'zdfheute-whatsapp-channel'))"
                    " or contains(@alt, 'Autorenfoto')]"
                ),
                caption_selector=XPath(
                    "./ancestor::*[(self::div and @class='c1owvrps c10o8fzf') or self::figure]//*[contains(@class,'c1pbsmr2')]"
                ),
                author_selector=XPath(
                    "./ancestor::*[(self::div and @class='c1owvrps c10o8fzf') or self::figure]//small[contains(@class, 'tsdggcs')]"
                ),
                lower_boundary_selector=XPath("//div[@class='s1am5zo f1uhhdhr']"),
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()

        _paragraph_selector = XPath(
            "//main/div[@data-testid='text-module']/div[@class='c10o8fzf']/p[@class='r1nj4qn5 rvqyqzi']|"
            "//figure/blockquote"
        )
        _topic_selector = XPath("//div[@class='t130q2hl']//a")

        @attribute
        def topics(self) -> List[str]:
            topic_string = strip_nodes_to_text(self._topic_selector(self.precomputed.doc), join_on=",")
            if topic_string is not None:
                return generic_topic_parsing(topic_string, delimiter=",")
            return []
