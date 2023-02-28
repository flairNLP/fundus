import datetime
from typing import Optional, List

import requests

from src.parser.html_parser import BaseParser, register_attribute
from src.parser.html_parser.utility import strip_nodes_to_text, generic_date_parsing, generic_author_parsing, \
    generic_topic_parsing


class MDRParser(BaseParser):

    @register_attribute
    def plaintext(self) -> Optional[str]:
        if nodes := self.precomputed.doc.cssselect('div.paragraph'):
            return strip_nodes_to_text(nodes)

    @register_attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get('news_keywords'))

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search('datePublished'))

    @register_attribute
    def authors(self) -> List[str]:
        return generic_author_parsing(self.precomputed.ld.bf_search('author'))

    @register_attribute
    def title(self) -> Optional[str]:
        return self.precomputed.ld.bf_search('headline')


if __name__ == '__main__':
    url = 'https://www.mdr.de/nachrichten/sachsen-anhalt/halle/halle/preise-lebensmittel-wenig-einkommen-100.html'

    html = requests.get(url).text

    example_parser = MDRParser()
    print(
        f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.attributes())}'")

    article = example_parser.parse(html)
    print(article)
