import datetime
import re
from typing import Optional, List, Match

from src.parser.html_parser import BaseParser, register_attribute
from src.parser.html_parser.utility import generic_plaintext_extraction_with_css, generic_author_extraction, \
    generic_date_extraction


class FocusParser(BaseParser):

    @register_attribute
    def plaintext(self) -> Optional[str]:
        return generic_plaintext_extraction_with_css(self.precomputed.doc,
                                                     "div .leadIn > p, "
                                                     "div .textBlock > p, "
                                                     "div .textBlock > h2")

    @register_attribute
    def authors(self) -> List[str]:
        return generic_author_extraction(self.precomputed.ld, ["author"])

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_extraction(self.precomputed.ld)

    @register_attribute
    def title(self):
        return self.ld().get('headline')

    @register_attribute
    def topics(self) -> List[str]:

        snippet = self.precomputed.doc.xpath(
            'string(//script[@type="text/javascript"][contains(text(), "window.bf__bfa_metadata")])')
        if not snippet:
            return []
        js: str = snippet.replace('\n', '')

        regex: str = r'\"hyscore\":{\s*\"keywords\":\[(.*?)]'
        parsed_topics: Optional[Match] = re.search(regex, str(js), flags=re.MULTILINE)
        if parsed_topics:
            result = parsed_topics.group(1).replace('\"', '').split(",")

        else:
            return []

        split_topics = []
        for topic_el in result:
            split = re.findall('[A-Z][^A-Z]*', topic_el)
            split_topics.append(" ".join(split))

        return split_topics
