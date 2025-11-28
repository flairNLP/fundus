import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class LTOParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("div.article-text-wrapper > p")
        _summary_selector = CSSSelector("div.reader__intro")
        _subheadline_selector = CSSSelector("div.article-text-wrapper > h2")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.meta.get("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            # Try to get date from meta tag or page content
            date_str = None
            date_elements = self.precomputed.doc.xpath('//p[@class="reader__meta-info"]')
            for elem in date_elements:
                text = elem.text_content().strip()
                # Check if it looks like a date (contains digits and dots)
                if text and any(c.isdigit() for c in text) and '.' in text:
                    date_str = text
                    break
            return generic_date_parsing(date_str)

        @attribute
        def topics(self) -> List[str]:
            keywords = self.precomputed.meta.get("keywords")
            if keywords:
                # Split by comma and clean up
                topics = [k.strip() for k in keywords.split(',')]
                # Filter out generic terms
                filtered = [t for t in topics if t and t not in ['Recht', 'aktuell', 'Nachrichten', 'News', 
                                                                   'Rechtsnews', 'Branchennews', 'Rechtsinformationen',
                                                                   'Rechtsprechung', 'Gesetzgebung', 'Justiz']]
                return filtered
            return []
