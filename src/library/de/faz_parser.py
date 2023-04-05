import datetime
from typing import List, Optional

from src.parsing import ArticleBody, BaseParser, attribute
from src.parsing.utility import (
    extract_article_body_with_selector,
    generic_date_parsing,
    generic_topic_parsing,
)


class FAZParser(BaseParser):
    @attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            summary_selector="div.atc-Intro > p",
            subheadline_selector="div.atc-Text > h3",
            paragraph_selector="div.atc-Text > p",
        )

    @attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get("keywords"))

    @attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

    @attribute
    def authors(self) -> List[str]:
        # Unfortunately, the raw data may contain cities. Most of these methods aims to remove the cities heuristically.
        if not (author_nodes := self.precomputed.doc.cssselect(".atc-MetaAuthor")):
            return []
        else:
            if len(author_nodes) > 1:
                # With more than one entry, we abuse the fact that authors are linked with an <a> tag,
                # but cities are not
                author_nodes = [node for node in author_nodes if bool(next(node.iterchildren(tag="a"), None))]
            return [text for node in author_nodes if "F.A.Z" not in (text := node.text_content())]

    @attribute
    def title(self) -> Optional[str]:
        return self.precomputed.meta.get("og:title")
