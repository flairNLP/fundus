import datetime
import re
from typing import List, Optional

from lxml.cssselect import CSSSelector
from lxml.etree import XPath
from lxml.html import fromstring, tostring

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    apply_substitution_pattern_over_list,
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class TimesOfIndiaParser(ParserProxy):
    class V1(BaseParser):
        _subheadline_selector = XPath(
            "(//div[@class='_s30J clearfix  '])[1]/div/b |"
            "(//div[@class='_s30J clearfix  '])[1]/div/h2 |"
            "(//div[@class='_s30J clearfix  '])[1]//span[contains(class, strong)]"
        )
        _paragraph_selector = XPath("(//div[@class='_s30J clearfix  '])[1]/p[text()]")
        _summary_selector = XPath("//div[@class='M1rHh undefined']")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            html_as_string = tostring(self.precomputed.doc).decode("utf-8")
            html_as_string = re.sub(r"(</div>)((\r\n|\r|\n)<br>)", "</div><p>", html_as_string)
            html_as_string = re.sub(r"</div>\s*</div>(?!<)", "</div></div><p>", html_as_string)
            html_as_string = re.sub(r"</div>\s*</div>\s*</div>(?!<)", "</div></div></div><p>", html_as_string)
            html_as_string = re.sub(r"<br>(\r\n|\r|\n)(:?<div)", "</p>", html_as_string)
            html_as_string = re.sub(r"(:?::before)(\r\n|\r|\n)", "<p>", html_as_string)
            html_as_string = re.sub(r"(\r\n|\r|\n)(:?::after)", "</p>", html_as_string)
            html_as_string = re.sub(r"<br>", "</p><p>", html_as_string)
            html_as_string = re.sub(
                r"<div class=\"_s30J clearfix  \">", "<div class=\"_s30J clearfix  \"><p class='intro'>", html_as_string
            )
            return extract_article_body_with_selector(
                fromstring(html_as_string),  # type: ignore
                summary_selector=self._summary_selector,
                paragraph_selector=self._paragraph_selector,
                subheadline_selector=self._subheadline_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return apply_substitution_pattern_over_list(
                generic_author_parsing(self.precomputed.ld.bf_search("author")),
                re.compile(r"(TOI .*|TIMESOFINDIA.COM)"),
            )

        @attribute
        def title(self) -> Optional[str]:
            if title := self.precomputed.meta.get("og:title"):
                return re.sub(r"( - Times.*| \| (India.*|.*News))", "", title)
            return None

        @attribute
        def topics(self) -> List[str]:
            return [
                topic.title()
                for topic in generic_topic_parsing(self.precomputed.meta.get("news_keywords"))
                if "News" not in topic.title()
            ]

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=CSSSelector("div.contentwrapper.clearfix"),
                lower_boundary_selector=CSSSelector("div.authorComment"),
                image_selector=CSSSelector("section.leadmedia img"),
                caption_selector=XPath(
                    "./ancestor::section[contains(@class, 'leadmedia')]//div[contains(@class, 'img_cptn')]"
                ),
                author_selector=re.compile(r"\((?P<credits>.*?)\)$"),
            )
