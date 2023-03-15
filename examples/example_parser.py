import datetime
from typing import List, Optional

import requests

from src.parser.html_parser import ArticleBody, BaseParser, register_attribute
from src.parser.html_parser.utility import (
    extract_article_body_with_selector,
    generic_date_parsing,
    generic_text_extraction_with_css,
    generic_topic_parsing,
)


class MDRParser(BaseParser):
    @register_attribute
    def body(self) -> ArticleBody:
        return extract_article_body_with_selector(
            self.precomputed.doc,
            summary_selector="p.einleitung",
            subheadline_selector="div > .subtitle",
            paragraph_selector="div.paragraph",
        )

    @register_attribute
    def topics(self) -> List[str]:
        return generic_topic_parsing(self.precomputed.meta.get("news_keywords"))

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

    @register_attribute
    def authors(self) -> List[str]:
        if author := generic_text_extraction_with_css(self.precomputed.doc, ".articleMeta > .author"):
            cleaned_author = author.replace("von", "").replace(" und ", ", ")
            return [name.strip() for name in cleaned_author.split(",")]
        return []

    @register_attribute
    def title(self) -> Optional[str]:
        return title if isinstance(title := self.precomputed.ld.bf_search("headline"), str) else None


if __name__ == "__main__":
    url = "https://www.mdr.de/nachrichten/sachsen-anhalt/halle/halle/preise-lebensmittel-wenig-einkommen-100.html"

    html = requests.get(url).text

    example_parser = MDRParser()
    print(
        f"This '{example_parser.__class__.__name__}' is capable of parsing '{', '.join(example_parser.attributes())}'"
    )

    article = example_parser.parse(html)
    print(article)
