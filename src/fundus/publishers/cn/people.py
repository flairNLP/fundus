import datetime
from typing import List, Optional

import lxml.html
from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute, function
from fundus.parser.utility import (
  extract_article_body_with_selector,
  generic_author_parsing,
  generic_date_parsing,
  parse_title_from_root,
)


class PeopleParser(ParserProxy):
  class V1(BaseParser):
      _paragraph_selector = CSSSelector("div.rm_txt_con > p")

      @function(priority=0)
      def fix_encoding(self):
          self.precomputed.html = self.precomputed.html.encode("latin-1").decode("gbk")
          self.precomputed.doc = lxml.html.document_fromstring(self.precomputed.html)

      @attribute
      def body(self) -> ArticleBody:
          return extract_article_body_with_selector(self.precomputed.doc, paragraph_selector=self._paragraph_selector)

      @attribute
      def title(self) -> Optional[str]:
          return parse_title_from_root(self.precomputed.doc)

      @attribute
      def authors(self) -> List[str]:
          return generic_author_parsing(self.precomputed.meta.get("author"))

      @attribute
      def publishing_date(self) -> Optional[datetime.datetime]:
          return generic_date_parsing(self.precomputed.meta.get("publishdate"))