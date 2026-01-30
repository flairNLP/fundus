import datetime
import re
from typing import List, Optional

import lxml.html
from lxml.etree import XPath

from fundus.parser import (
    ArticleBody,
    BaseParser,
    Image,
    ParserProxy,
    attribute,
    function,
)
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
    parse_json,
    transform_breaks_to_tag,
)


class HankookIlboParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2026, 1, 27)
        _paragraph_selector = XPath("//div[@itemprop='articleBody']/p[@class='editor-p']")
        _summary_selector = XPath("//div[@itemprop='articleBody']/h2")
        _subheadline_selector = XPath("//div[@itemprop='articleBody']/h3")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                doc=self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.xpath_search("//NewsArticle/author/name"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("news_keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//div[@itemprop='articleBody']"),
                image_selector=XPath("//div[@itemprop='articleBody']//div[@class='img-box']//img"),
                caption_selector=XPath("./ancestor::div[@class='editor-img-box']//div[@class='caption']"),
                author_selector=re.compile(r"(?!.*\.)(?P<credits>.*)"),
            )

    class V2(BaseParser):
        _paragraph_selector = XPath("//div[@class='article-view']/p[@class='editor-p']")
        _summary_selector = XPath("//div[@class='article-view']/h2")
        _subheadline_selector = XPath("//div[@class='article-view']/h3")

        _author_selector = XPath("//div[@class='article-view']//div[@class='writer']/span[@class='name']/strong")

        _content_selector = XPath(
            "string(//script[re:test(text(), 'contentHtml')])",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )
        _content_bloat_pattern = re.compile(r"\$\$.+?\$\$")

        @function(priority=1)
        def _parse_page_content(self) -> None:
            if content_script := parse_json(self._content_selector(self.precomputed.doc)):
                self.precomputed.ld.add_ld(content_script, "page-data")

                # parse+build content node
                content_html = (
                    f"<div class='article-view'>"
                    f"{self.precomputed.ld.xpath_search('//page-data//contentHtml', scalar=True)}"
                    f"</div>"
                )
                cleaned_content_html = re.sub(self._content_bloat_pattern, "", content_html)
                content_node = lxml.html.fromstring(cleaned_content_html)

                # parse summary node and add to content node
                summary_html = (
                    f"<h2>" f"{self.precomputed.ld.xpath_search('//page-data//subTitle', scalar=True)}" f"</h2>"
                )
                summary__node = lxml.html.fromstring(summary_html)
                content_node.insert(0, summary__node)
                transform_breaks_to_tag(summary__node, tag="h2", replace=True)

                # insert content node
                self.precomputed.doc.body.insert(0, content_node)

        @attribute
        def body(self) -> Optional[ArticleBody]:
            return extract_article_body_with_selector(
                doc=self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing([node.text_content() for node in self._author_selector(self.precomputed.doc)])

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(
                self.precomputed.ld.xpath_search("//page-data//detail/deployDt", scalar=True),
                tz=datetime.timezone(datetime.timedelta(hours=9)),
            )

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("headline")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("news_keywords"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//div[@class='article-view']"),
                image_selector=XPath("//div[@class='article-view']//img"),
                caption_selector=XPath("./ancestor::div[@class='editor-img-box']//div[@class='caption']"),
                author_selector=re.compile(r"(?!.*\.)(?P<credits>.*)"),
            )
