import datetime
import json
from typing import Optional, List

import dateutil.parser
import lxml.html

from src.html_parser import BaseParser
from stream.utils import listify


class DieWeltParser(BaseParser):

    @BaseParser.register_function(priority=0)
    def setup(self):
        content: str = self.cache.get('html')
        doc = lxml.html.fromstring(content)
        ld_content = doc.xpath('string(//script[@type="application/ld+json"]/text())')
        ld = json.loads(ld_content) or {}
        meta = self.Utility.get_meta_content(doc) or {}
        self.share(doc=doc, ld=ld, meta=meta)

    @BaseParser.register_filter(priority=1)
    def filter(self) -> bool:
        if not (article_type := self.cache['ld'].get('@type')):
            return True
        if article_type == 'VideoObject' or article_type == "LiveBlogPosting":
            return True
        return False

    @BaseParser.register_attribute
    def plaintext(self) -> Optional[str]:
        doc: lxml.html.HtmlElement = self.cache.get('doc')
        selector: str = (
            "body .c-summary > div, "
            "body .c-article-text > p"
        )
        if nodes := doc.cssselect(selector):
            return self.Utility.strip_nodes_to_text(nodes)

    @BaseParser.register_attribute
    def authors(self) -> List[str]:
        if author_entries := self.cache['ld'].get('author'):
            return [entry['name'] for entry in listify(author_entries) if entry.get('name')]
        else:
            return []

    @BaseParser.register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        if iso_date_str := self.cache['ld'].get('datePublished'):
            return dateutil.parser.parse(iso_date_str)

    @BaseParser.register_attribute
    def title(self):
        return self.cache['ld'].get('headline')

    @BaseParser.register_attribute
    def topics(self) -> List[str]:
        if keyword_str := self.cache['meta'].get('keywords'):
            return keyword_str.split(',')
