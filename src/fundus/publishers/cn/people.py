import datetime
from typing import List, Optional

from lxml.html import document_fromstring
from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.data import TextSequence
from fundus.parser.utility import (
    generic_author_parsing,
    generic_date_parsing,
)


class PeopleParser(ParserProxy):
    class V1(BaseParser):

        @attribute
        def body(self) -> ArticleBody:
            root = document_fromstring(self.precomputed.html)
            # rm_txt_con cf
            selector = CSSSelector('div.rm_txt_con > p')
            nodes = selector(root)
            for node in nodes:
                print(node.text_content().encode("latin-1").decode("gbk"))
            article = [node.text_content().encode("latin-1").decode("gbk") for node in nodes]
            return ArticleBody(TextSequence([]), article)

        @attribute
        def title(self) -> Optional[str]:
            root = document_fromstring(self.precomputed.html)
            selector = CSSSelector('title')
            return selector(root)[0].text_content().strip().encode("latin-1").decode("gbk")

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get('author'))

        @attribute
        def published_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get('publishdate'))


