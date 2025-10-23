import datetime
import re
from typing import List, Optional

from lxml.etree import XPath
from lxml.html import HtmlElement, fromstring, tostring

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class WinfutureParser(ParserProxy):
    class V1(BaseParser):
        _paragraph_selector = XPath("//div[@id='news_content']/p")
        _summary_selector = XPath("//div[@id='news_content']//div[@class='teaser_text']")
        _subheadline_selector = XPath("//div[@id='news_content']/h2")

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.meta.get("og:title")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            html_as_string = tostring(self.precomputed.doc).decode("utf-8")
            # Most paragraphs are separated by two <br>> tags, depending on if there is text
            # around those tags you need either opending or closing tags or both.
            html_as_string = re.sub(r"(<br>){2}\n<h2", "<h2", html_as_string)
            html_as_string = re.sub(r"(<br>){2}\n<(div|script)", "</p>\n<div", html_as_string)
            html_as_string = re.sub(r"(<br>){2}", "</p>\n<p>", html_as_string)
            # Subheadlines mark the beginning of a new paragraph
            html_as_string = re.sub(r"(</h2>)", "</h2>\n<p>", html_as_string)
            # Subheadlines mark the end of a paragraph
            html_as_string = re.sub(r"(?<![\W>])\n(?=<h2>)", "</p>\n", html_as_string)
            # Edge cases of paragraphs beginning/starting with various other Elements
            html_as_string = re.sub(r"(?<=<br>)\n(?!([<\W]))", "\n<p>", html_as_string)
            html_as_string = re.sub(r"(?<=(ipt|div)>)\n(?![\W<])", "\n<p>", html_as_string)
            html_as_string = re.sub(r"(?<![\W>])\n(?=<[a-z0-9=_'\"]*>)", "</p>\n", html_as_string)
            doc: HtmlElement = fromstring(html_as_string)  # type: ignore
            return extract_article_body_with_selector(
                doc=doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("article:tag"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                image_selector=XPath("//div[@class='primary_content']//img[@class='teaser_img' or @class='photo']"),
                upper_boundary_selector=XPath("//div[@class='primary_content']"),
                lower_boundary_selector=XPath("//div[@class='mb20 more_links']"),
                caption_selector=XPath("./ancestor::span[contains(@class,'hmedia')]//a"),
                author_selector=XPath(
                    "./ancestor::div[@class='teaser_img_container']//div[@class='teaser_img_source']"
                ),
            )
