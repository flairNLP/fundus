import datetime
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_nodes_to_text,
    generic_topic_parsing,
    image_extraction,
    parse_title_from_root,
)


class NetzpolitikOrgParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = CSSSelector("div.entry-content p")
        _summary_selector = CSSSelector("div.entry-excerpt > p")
        _subheadline_selector = CSSSelector("div.entry-content > h3")
        _author_selector = CSSSelector("span > a[rel='author'], .np-intro-author-name-list a")
        _topic_selector = CSSSelector("div.entry-footer__tags li, .wp-block-post-terms a")

        _bloat_topics = {"Netzpolitischer Wochenrückblick"}

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title") or parse_title_from_root(self.precomputed.doc)

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(
                generic_nodes_to_text(self._topic_selector(self.precomputed.doc), normalize=True),
                result_filter=self._bloat_topics,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(generic_nodes_to_text(self._author_selector(self.precomputed.doc)))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                image_selector=XPath("//figure//img[not(contains(@class, 'author-avatars'))]"),
                paragraph_selector=self._paragraph_selector,
                caption_selector=XPath("./ancestor::figure//figcaption/text()"),
                author_selector=XPath("./ancestor::figure//figcaption/span"),
            )
