import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
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


class BRParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2024, 8, 26)

        _summary_selector = XPath(
            "//div[starts-with(@class, 'ArticleHeader_section')]//p[starts-with(@class, 'ArticleModuleTeaser_teaserText') or starts-with(@class, 'ArticleItemTeaserText_text')]"
        )
        # paragraph_selector captures div contents for full article, p for teaser-only flash articles
        _paragraph_selector = XPath("(//div[starts-with(@class, 'ArticleModuleText_content')])[1]//p")

        _subheadline_selector = XPath(
            "//section[starts-with(@class, 'ArticleModuleText_wrapper')]//div[starts-with(@class, 'ArticleModuleText_content')]//h2"
        )

        @attribute
        def title(self) -> Optional[str]:
            return title if isinstance(title := self.precomputed.ld.bf_search("headline"), str) else None

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.ld.bf_search("keywords"))

        @attribute
        def images(self) -> List[Image]:
            author_pattern: str = r"(?<=\|\sBild:\s).*$"
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//figure[not(parent::aside)]//img"),
                author_selector=XPath(
                    f"re:match(./@title, '{author_pattern}')",
                    namespaces={"re": "http://exslt.org/regular-expressions"},
                ),
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()

        _bloat_pattern = "Das ist die Europäische Perspektive bei BR24."
        _summary_selector = XPath("//header //p[@class='body3 ArticleItemTeaserText_text__H_RS_']")
        _subheadline_selector = XPath("//section[@id='articlebody'] //h2[text()]")
        _paragraph_selector = XPath(
            f"//section[@id='articlebody'] //section[@class='ArticleModuleText_wrapper__AyX6M'] //p[text() and not(re:test(string(), '{_bloat_pattern}'))] |"
            "//section[@id='articlebody'] //section[@class='ArticleModuleText_wrapper__AyX6M'] //li |"
            "//section[@class='ShortnewsDetail_content__79bZq'] //p[1]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )

        _date_selector = CSSSelector("p.ShortnewsDetail_source__2ep85.heading4")

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            if date_nodes := self._date_selector(self.precomputed.doc):
                if (content := date_nodes[0].text) is None:
                    return None
                date_string = content.split(",")[-1]
                tz_aware_date = date_string.replace("Uhr", "+02:00")
                return generic_date_parsing(tz_aware_date)
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))
