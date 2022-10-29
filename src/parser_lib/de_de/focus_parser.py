import datetime
import re
from typing import Optional, List

from dateutil import parser

from src.html_parser import BaseParser
from src.html_parser.base_parser import register_attribute
from src.html_parser.utility import extract_plaintext_from_css_selector


class FocusParser(BaseParser):
    """
    This parser is for the old format!
    """

    @register_attribute
    def plaintext(self) -> Optional[str]:
        return extract_plaintext_from_css_selector(self.cache['doc'],
                                                   "div .leadIn > p, "
                                                   "div .textBlock > p, "
                                                   "div .textBlock > h2")

    @register_attribute
    def authors(self) -> List[str]:
        raw_str = self.ld().get('author').get("name")
        if raw_str:
            return [raw_str]
        else:
            return []

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:

        iso_date_str = self.ld().get('datePublished')

        return parser.parse(iso_date_str)

    @register_attribute
    def title(self):
        return self.ld().get('headline')

    @register_attribute
    def topics(self) -> List[str]:

        snippet = self.cache['doc'].xpath(
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
