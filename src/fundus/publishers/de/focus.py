import datetime
import re
from typing import List, Match, Optional, Pattern

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    image_extraction,
)


class FocusParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("div.textBlock > p , div[data-qa-article-content-text] > p")
        _summary_selector = CSSSelector("div.leadIn > p, div.Article-Description ")
        _subheadline_selector = CSSSelector("div.textBlock > h2, div[data-qa-article-content-text] > h2")
        _snippet_selector = XPath(
            'string(//script[@type="text/javascript"][contains(text(), "window.bf__bfa_metadata")])'
        )

        # regex patterns
        _author_substitution_pattern: Pattern[str] = re.compile(
            r"Von FOCUS-online-(Redakteur|Autorin|Reporter|Redakteurin|Gastautor)\s"
        )
        _topic_pattern: Pattern[str] = re.compile(r'"keywords":\[{(.*?)}\]')
        _topic_name_pattern: Pattern[str] = re.compile(r'"name":"(.*?)"', flags=re.MULTILINE)

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
            author_names = generic_author_parsing(self.precomputed.ld.bf_search("author"))
            for i, name in enumerate(author_names):
                author_names[i] = re.sub(self._author_substitution_pattern, "", name)
            return author_names

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            snippet = self._snippet_selector(self.precomputed.doc)
            if not snippet:
                return []

            match: Optional[Match[str]] = re.search(self._topic_pattern, snippet)
            if not match:
                return []
            topic_names: List[str] = re.findall(self._topic_name_pattern, match.group(1))

            return topic_names

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//div[@class='image clearfix']//img|//figure//img"),
                caption_selector=XPath(
                    "./ancestor::div[@class='image clearfix']//span[@class='caption']|"
                    "./ancestor::figure//span[@class='Image-Caption']"
                ),
                author_selector=XPath(
                    "./ancestor::div[@class='image clearfix']//span[@class='source']|"
                    "./ancestor::figure//span[@class='Image-Credit']"
                ),
                lower_boundary_selector=XPath("//footer"),
            )
