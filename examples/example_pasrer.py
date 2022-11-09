import datetime
from typing import Optional

import dateutil.parser
import requests

from src.parser.html_parser import BaseParser, register_attribute
from src.parser.html_parser.utility import strip_nodes_to_text


class MDRParser(BaseParser):

    @register_attribute(priority=4)
    def plaintext(self) -> Optional[str]:
        doc = self.cache['doc']
        if nodes := doc.cssselect('div.paragraph'):
            return strip_nodes_to_text(nodes)

    @register_attribute
    def topics(self) -> Optional[str]:
        if topics := self.meta().get('news_keywords'):
            return topics

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        if date_string := self.ld().get('datePublished'):
            return dateutil.parser.parse(date_string)

    @register_attribute
    def authors(self) -> str:
        if author_dict := self.ld().get('author'):
            return author_dict.get('name')

    @register_attribute(priority=4)
    def title(self) -> Optional[str]:
        return self.ld().get('headline')


if __name__ == '__main__':
    url = 'https://www.mdr.de/nachrichten/sachsen-anhalt/halle/halle/preise-lebensmittel-wenig-einkommen-100.html'

    html = requests.get(url).text

    example_parser = MDRParser()
    print(
        f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.attributes())}'")

    article = example_parser.parse(html)
    print(article)
