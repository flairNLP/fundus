import json
from datetime import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute, utility


class KrautreporterParser(ParserProxy):
    class V1(BaseParser):
        _summary_selector = CSSSelector("p.article-headers-standard__teaser")
        _subheadline_selector = CSSSelector("div.article-markdown > h2")
        _paragraph_selector = CSSSelector("div.article-markdown > p")
        _json_ld_selector = CSSSelector('script[type="application/ld+json"]')
        _topic_selector = CSSSelector("div.article-headers-shared-topic")

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def body(self) -> ArticleBody:
            article_body = utility.extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )
            return article_body

        @attribute
        def authors(self) -> List[str]:
            author_string = self.precomputed.meta.get("author")
            return utility.generic_author_parsing(author_string)

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            json_ld = self._get_json_ld_dict()
            date_string = json_ld.get("@graph", [])[0]["datePublished"]
            return utility.generic_date_parsing(date_string)

        @attribute
        def topics(self) -> List[str]:
            topic_element = self._topic_selector(self.precomputed.doc)[0]
            return utility.generic_topic_parsing(topic_element.text_content())

        def _get_json_ld_dict(self):
            """
            Since the JSON-LD is wrapped in a CDATA block we need to implement this workaround
            """
            # NOTE: Maybe cleaner to override BaseParser._base_setup (also because of free_access attribute)
            json_ld_element = self._json_ld_selector(self.precomputed.doc.head)[0]
            json_ld_string = json_ld_element.text_content()
            json_ld_string = json_ld_string.replace("//<![CDATA[", "").replace("//]]>", "")
            json_ld = json.loads(json_ld_string)            
            return json_ld