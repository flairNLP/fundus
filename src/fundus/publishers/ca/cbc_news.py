import datetime
import json
import re
from typing import List, Optional

import lxml
import more_itertools
from lxml.cssselect import CSSSelector
from lxml.etree import XPath
from lxml.html import document_fromstring

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.base_parser import Precomputed, logger
from fundus.parser.data import LinkedDataMapping
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    get_meta_content,
)


class CBCNewsParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("h2.deck")
        _subheadline_selector = CSSSelector("div.story > h2")
        _paragraph_selector = CSSSelector("div.story > p")
        _cbc_ld_selector: XPath = XPath("//script[@type='application/ld+json' or @id='initialStateDom']")

        def _base_setup(self, html: str) -> None:
            doc = lxml.html.document_fromstring(html)
            ld_nodes = self._cbc_ld_selector(doc)
            lds = []
            for node in ld_nodes:
                try:
                    json_object = json.loads(re.sub(r"(window\.__INITIAL_STATE__ = |;$)", "", node.text_content()))
                    if not json_object.get("@type"):
                        json_object["@type"] = "FurtherDetails"
                    lds.append(json_object)
                except json.JSONDecodeError as error:
                    logger.debug(f"Encountered {error!r} during LD parsing")
            collapsed_lds = more_itertools.collapse(lds, base_type=dict)
            self.precomputed = Precomputed(html, doc, get_meta_content(doc), LinkedDataMapping(collapsed_lds))

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("authorList"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            if not (title := self.precomputed.meta.get("og:title")):
                return title
            return re.sub(r" \|.*", "", title)

        @attribute
        def topics(self) -> List[str]:
            topic_dict = self.precomputed.ld.bf_search("keywords")
            topic_list = [v.get("name") for v in topic_dict.get("tags")]
            for v in topic_dict.get("concepts"):
                topic_list.append(re.sub(r".*/", "", v.get("path")))
            return topic_list
