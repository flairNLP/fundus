import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.data import Image
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_nodes_to_text,
    generic_topic_parsing,
    image_extraction,
)

_BLOAT_TOPICS = {
    "Curated",
    "News",
    "Newsroom daily",
    "story",
    "Canada",
    "World",
    "politics",
    "Business",
    "Travel",
    "Entertainment",
}


class PostMediaParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath(
            "//div[@class='story-v2-content-element-inline']/p[text() and not(text()='National Post')]"
        )
        _subheadline_selector = XPath(
            "//div[@class='story-v2-content-element-inline']/h3[not(@class)] |"
            "//div[@class='story-v2-content-element-inline']/p/strong",
        )
        _summary_selector = CSSSelector("article p.article-subtitle")

        _bloat_topics = _BLOAT_TOPICS
        _topic_filter = re.compile(
            r"([0-9a-f]{8}-([0-9a-f]{4}-){3}[0-9a-f]{12}|NLP Entity Tokens|NLP Category|NP Comment|Category):?\s*"
        )

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(
                self.precomputed.ld.bf_search("keywords"),
                substitution_pattern=self._topic_filter,
                result_filter=self._bloat_topics,
            )

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("(//div[@class='story-v2-block story-v2-article-container'])[1]"),
                lower_boundary_selector=XPath("//section[@class='article-content__share-group']"),
                caption_selector=XPath("./ancestor::figure/figcaption/span[@class='caption']"),
                author_selector=XPath("./ancestor::figure/figcaption/span[@class='credit' or @class='distributor']"),
            )

    class V2(BaseParser):
        _content_container = (
            "(//div[contains(concat(' ', normalize-space(@class), ' '), ' article-content__content-group ')] |"
            " //main/div[@class='entry-content'])"
        )
        _content = f"({_content_container} | {_content_container}/div[contains(@class, 'pm-classic-editor-content')])"

        _paragraph_selector = XPath(
            f"{_content}/p[normalize-space()] |"
            f"{_content}/div[starts-with(@class, 'components_paragraph')]/p[normalize-space()] |"
            f"{_content}/div[contains(@class, 'stack-hive-heading-section')][normalize-space()] |"
            f"{_content}/*[self::ul or self::ol][not(contains(@class, 'pmd-related-links'))]/li[normalize-space()]"
        )
        _subheadline_selector = XPath(f"{_content}/*[self::h2 or self::h3 or self::h4][normalize-space()]")
        _summary_selector = XPath(
            "//p[contains(@class, 'postmedia-article-topper__excerpt') or contains(@class, 'pm-cover-article-topper__excerpt')]"
        )
        _author_selector = XPath("(//div[@class='author-meta__byline'])[1]//*[contains(@class, 'author-meta__author')]")
        _author_filter = re.compile(r"^(Advertisement|Special to .+)$")

        _bloat_topics = _BLOAT_TOPICS
        _topic_filter = re.compile(r"(Category):?\s*")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            if author_nodes := self._author_selector(self.precomputed.doc):
                return generic_author_parsing(
                    generic_nodes_to_text(author_nodes, normalize=True), result_filter=self._author_filter
                )
            return generic_author_parsing(self.precomputed.meta.get("author"), result_filter=self._author_filter)

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.xpath_search("//Article/headline", scalar=True)

        @attribute
        def topics(self) -> List[str]:
            _combined_bloat_topics = re.compile(r"^\d+$|" + r"|".join(self._bloat_topics))
            topics = generic_topic_parsing(
                self.precomputed.ld.xpath_search("//Article/keywords|//NewsArticle/keywords"),
                substitution_pattern=self._topic_filter,
                result_filter=_combined_bloat_topics,
            )
            return list(set(t.title() for t in topics))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath(
                    "(//article[contains(@class, 'postmedia-article-topper')] |"
                    " //div[contains(@class, 'pm-cover-article-topper')])[1]"
                ),
                author_selector=[
                    re.compile(
                        r"(?:\s*\((?:(?i:photo)[^()]*|[^()a-z]+|[^()]*/[^()]*)\))*\s*\((?P<credits>[^()]+)\)\s*$"
                    ),
                    re.compile(r"\s*(?i:photo(?:graph)? by:?)\s+(?P<credits>.+?)\s*$"),
                    re.compile(r"\s*(?P<credits>(?i:photo supplied|supplied(?: image| photo)?|handout))\.?\s*$"),
                ],
            )
