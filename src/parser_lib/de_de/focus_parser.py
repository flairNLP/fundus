import datetime
import re
from typing import Optional, List, Match

import dateutil.parser
import lxml.html

from src.html_parser import BaseParser
from src.html_parser.base_parser import register_attribute
from src.html_parser.utility import strip_nodes_to_text
from stream.utils import listify


class FocusParser(BaseParser):

    @register_attribute
    def plaintext(self) -> Optional[str]:
        doc: lxml.html.HtmlElement = self.cache['doc']
        text_node_selector: str = (
            "div .leadIn > p, "
            "div .textBlock > p, "
            "div .textBlock > h2"
        )
        if nodes := doc.cssselect(text_node_selector):
            return strip_nodes_to_text(nodes)

    @register_attribute
    def authors(self) -> List[str]:
        if author_entries := self.ld().get('author'):
            return [entry['name'] for entry in listify(author_entries) if entry.get('name')]
        else:
            return []

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        if iso_date_str := self.ld().get('datePublished'):
            return dateutil.parser.parse(iso_date_str)

    @register_attribute
    def title(self):
        return self.ld.get('headline')

    @register_attribute
    def topics(self) -> List[str]:

        # topic extraction right here at the start, because we need to toss the article if it doesn't work
        snippet = self.cache["doc"].xpath(
            'string(//script[@type="text/javascript"][contains(text(), "window.bf__bfa_metadata")])')

        js: str = snippet.replace('\n', '')

        regex: str = r'\"hyscore\":{\s*\"keywords\":\[(.*?)]'
        parsed_topics: Optional[Match] = re.search(regex, str(js), flags=re.MULTILINE)
        result = parsed_topics.group(1).replace('\"', '').split(",")

        split_topics = []
        for topic_el in result:
            split = re.findall('[A-Z][^A-Z]*', topic_el)
            split_topics.append(" ".join(split))
        result = split_topics

        return result
