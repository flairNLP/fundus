import re
from datetime import date, datetime
from typing import List, Optional

import lxml.html
from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import (
    ArticleBody,
    BaseParser,
    Image,
    ParserProxy,
    attribute,
    function,
)
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class TheNationParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = date(2023, 7, 22)

        # There is a known issue preventing lxml from extracting text content within
        # the specified summary node.
        # This is due to invalid XML provided by The Nation.
        # Currently(lxml 4.9.3), lxml does not accept p tags within any heading (h*) tag.
        # The "correct" selector would be ".article-header-content > h2 > p"
        _summary_selector: XPath = CSSSelector(".article-header-content > h2")
        _paragraph_selector: XPath = CSSSelector(".article-body-inner > p")
        _aside_selector = CSSSelector("aside")

        _html_fix_pattern = re.compile(r'name="sft_double_opt_sail"\s*value="yes"\s/>\s*</form>')

        # there is a known issue with broken HTML regarding this publisher.
        # div.cta subtree is malformed, there is a missing closing div tag before the </form> tag, which
        # prevents lxml from properly parsing the text. I don't know if this is also a problem within V1,
        # but better safe than sorry, so I added it to V1 base class
        @function(priority=1)
        def _fix_malformed_html(self) -> None:
            if self.precomputed.doc.xpath("//div[contains(@id, 'cta-block')]"):
                fixed_html = re.sub(
                    self._html_fix_pattern,
                    'name="sft_double_opt_sail"value="yes"/></div></form>',
                    self.precomputed.html,
                )
                self.precomputed.doc = lxml.html.document_fromstring(fixed_html)

        # We remove aside tags here because the provided HTML does not enclose <p> tags
        # within .article-header-content. As a result, <aside> tags following <p> tags get attached
        # to the paragraph. This is valid HTML5 behaviour.
        # see https://stackoverflow.com/questions/8460993/p-end-tag-p-is-not-needed-in-html
        @function(priority=3)
        def _remove_aside(self) -> None:
            for aside in self._aside_selector(self.precomputed.doc):
                if (parent := aside.getparent()) is not None:
                    parent.remove(aside)

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("sailthru.author"))

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("keywords"))

        @attribute(priority=2)
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//h1[contains(@class,'title')]"),
                image_selector=CSSSelector(".image img"),
                caption_selector=XPath("(./ancestor::aside[contains(@class, 'image')])[1]//p[@class='caption']/text()"),
                author_selector=XPath(
                    "(./ancestor::aside[contains(@class, 'image')])[1]//p[@class='caption']/span[@class='credits']"
                ),
            )

    class V2(V1):
        VALID_UNTIL = date.today()

        # oh boy, TheNation is really a mess. they changed the layout 2023|7|22 but somehow the old articles still
        # use the old layout for main content, so we concatenate XPath from V1 onto V1_1.

        _summary_selector = XPath(
            "//div[@class='article-header-content'] /h2 | //div[contains(@class, 'article-title')] /p"
        )
        _paragraph_selector = XPath("(//article | //div[@class='article-body-inner']) / p")

        # remove aside function from V1
        def _remove_aside(self):
            pass

        @attribute
        def topics(self) -> List[str]:
            if topics := generic_topic_parsing(self.precomputed.meta.get("keywords")):
                return topics
            else:
                return generic_topic_parsing(self.precomputed.meta.get("sailthru.tags"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//h1[contains(@class,'title')]"),
                caption_selector=XPath("./ancestor::figure//figcaption/text()|./ancestor::figure//figcaption/p"),
            )
