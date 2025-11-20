from datetime import datetime
from typing import List, Optional, Any
from lxml.cssselect import CSSSelector
from lxml.etree import XPath
from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
  extract_article_body_with_selector,
  generic_author_parsing,
  generic_date_parsing,
)


class VnExpressIntlParser(ParserProxy):
  class V1(BaseParser):
    _summary_selector = CSSSelector("p.description")
    _paragraph_selector = CSSSelector("article.fck_detail > p")
    _subheadline_selector = CSSSelector("article.fck_detail > h2")
      
    @attribute
    def title(self) -> Optional[str]:
      title_list: List[Any] = self.precomputed.ld.xpath_search("//NewsArticle/headline")
      if title_list and isinstance(title_list[0], str):
        title: str = title_list[0]
        return title
      
      title_meta = self.precomputed.meta.get("og:title")
      if title_meta and isinstance(title_meta, str):
        return title_meta
      
      title_nodes = CSSSelector("h1.title-detail")(self.precomputed.doc)
      if title_nodes:
        title_text: str = title_nodes[0].text_content().strip()
        return title_text
      
      return None
    
    @attribute
    def authors(self) -> List[str]:
      author_data_list: List[Any] = self.precomputed.ld.xpath_search("//NewsArticle/author")
      if author_data_list:
        author_ld = author_data_list[0]
        authors = generic_author_parsing(author_ld)
        if authors:
          return authors
      
      author_nodes = CSSSelector("p.author_mail strong")(self.precomputed.doc)
      if author_nodes:
        return [node.text_content().strip() for node in author_nodes if node.text_content().strip()]
      
      return []
    
    @attribute
    def publishing_date(self) -> Optional[datetime]:
      date_list: List[Any] = self.precomputed.ld.xpath_search("//NewsArticle/datePublished")
      if date_list and isinstance(date_list[0], str):
        date_str: str = date_list[0]
        return generic_date_parsing(date_str)
      
      date_meta = self.precomputed.meta.get("article:published_time")
      if date_meta and isinstance(date_meta, str):
        return generic_date_parsing(date_meta)
      
      return None
  
    @attribute
    def body(self) -> Optional[ArticleBody]:
      return extract_article_body_with_selector(
        self.precomputed.doc,
        summary_selector=self._summary_selector,
        paragraph_selector=self._paragraph_selector,
        subheadline_selector=self._subheadline_selector,
      )
  
    def _parse_ld_keywords(self) -> List[str]:
      keywords_list: List[Any] = self.precomputed.ld.xpath_search("//NewsArticle/keywords")
      
      if not keywords_list:
        return []
      
      keywords = keywords_list[0] if keywords_list else None

      result: List[str] = []
      if isinstance(keywords, list):
        for item in keywords:
          if isinstance(item, str):
            result.extend([k.strip() for k in item.split(',') if k.strip()])
          elif isinstance(item, list):
            result.extend([k.strip() for k in item if isinstance(k, str) and k.strip()])
      elif isinstance(keywords, str):
        result = [k.strip() for k in keywords.split(',') if k.strip()]
      
      return result

    def _parse_meta_topics(self) -> List[str]:
      section = self.precomputed.meta.get("article:section")
      if section and isinstance(section, str):
        return [section]
      meta_keywords = self.precomputed.meta.get("keywords")
      if meta_keywords and isinstance(meta_keywords, str):
        return [k.strip() for k in meta_keywords.split(',') if k.strip()]
      return []

    @attribute
    def topics(self) -> List[str]:
      ld_topics = self._parse_ld_keywords()
      if ld_topics:
        return ld_topics
      return self._parse_meta_topics()