import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.base_parser import function
from fundus.parser.data import Image
from fundus.parser.utility import (
    extract_article_body_with_selector,
    extract_json_from_dom,
    generic_author_parsing,
    generic_date_parsing,
    image_extraction,
)


class CBCNewsParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("h2.deck")
        _subheadline_selector = CSSSelector("div.story > h2")
        _paragraph_selector = CSSSelector("div.story > p")

        _cbc_ld_selector: XPath = XPath("//script[@id='initialStateDom']")

        @function(priority=1)
        def _parse_initial_state_dom(self):
            state_dom_json = extract_json_from_dom(self.precomputed.doc, self._cbc_ld_selector)
            for ld in state_dom_json:
                self.precomputed.ld.add_ld(ld, "initialStateDom")

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
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            if not (topic_dict := self.precomputed.ld.bf_search("keywords")):
                return []

            # add locations
            topic_list = [topic for location in topic_dict.get("tags") if (topic := location.get("name")) is not None]

            # add subjects
            for subject in topic_dict.get("concepts"):
                if (path := subject.get("path")) is not None:
                    topic_list.append(re.sub(r".*/", "", path))

            return topic_list

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//div[@data-cy='storyWrapper']"),
                caption_selector=XPath(
                    "./ancestor::figure//figcaption | ./ancestor::span[contains(@class,'mediaEmbed')]/span"
                ),
                author_selector=re.compile(r"\((?P<credits>.*?)\)$"),
            )
