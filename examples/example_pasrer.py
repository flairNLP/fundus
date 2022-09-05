import datetime
import json
from collections import defaultdict

import dateutil.parser
import lxml.html
import requests

from html_parser import BaseParser


class MDRParser(BaseParser):

    @BaseParser.register_filter(priority=1)
    def filter(self):
        return False

    @BaseParser.register_control(priority=2)
    def setup(self):
        content = self.cache.get('html')
        doc: lxml.html.HtmlElement = lxml.html.fromstring(content)
        ld_content = doc.xpath('string(//script[@type="application/ld+json"]/text())')
        ld = json.loads(ld_content)
        meta = self.Utility.get_meta_content(doc)
        self.share(doc=doc, ld=defaultdict(dict, ld), meta=meta)

    @BaseParser.register_attribute(priority=4)
    def plaintext(self) -> str:
        doc = self.cache.get('doc')
        nodes = doc.cssselect('div.paragraph')
        return self.Utility.strip_nodes_to_text(nodes)

    @BaseParser.register_attribute
    def topics(self):
        topics = self.cache.get('meta').get('news_keywords')
        return topics

    @BaseParser.register_attribute
    def publishing_date(self) -> datetime.datetime:
        if date_string := self.cache.get('ld').get('datePublished'):
            return dateutil.parser.parse(date_string)

    @BaseParser.register_attribute
    def authors(self) -> str:
        if author_dict := self.cache.get('ld').get('author'):
            return author_dict.get('name')

    @BaseParser.register_attribute(priority=4)
    def title(self) -> str:
        return self.cache.get('ld').get('headline')


if __name__ == '__main__':
    url = 'https://www.mdr.de/nachrichten/sachsen-anhalt/halle/halle/preise-lebensmittel-wenig-einkommen-100.html'

    html = requests.get(url).text

    example_parser = MDRParser()
    print(f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.attributes)}'")

    article = example_parser.parse(html)
    print(article)
