import datetime
import re
from typing import List, Optional

from lxml.etree import XPath
from lxml.html import fromstring, tostring

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute
from fundus.parser.utility import (
    apply_substitution_pattern_over_list,
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
)


class TimesOfIndiaParser(ParserProxy):
    class V1(BaseParser):
        _subheadline_selector = XPath(
            "(//div[@class='_s30J clearfix  '])[1]/div/b |" "(//div[@class='_s30J clearfix  '])[1]/div/h2"
        )
        _paragraph_selector = XPath("(//div[@class='_s30J clearfix  '])[1]/p[not(@class='intro')]")
        _summary_selector = XPath("(//div[@class='_s30J clearfix  '])[1]/p[@class='intro']")

        @attribute
        def body(self) -> ArticleBody:
            html_as_string = tostring(self.precomputed.doc).decode("utf-8")
            html_as_string = re.sub(r"(</div>)((\r\n|\r|\n)<br>)", "</div><p>", html_as_string)
            html_as_string = re.sub(r"</div></div>(?!<)", "</div></div><p>", html_as_string)
            html_as_string = re.sub(r"</div></div></div>(?!<)", "</div></div></div><p>", html_as_string)
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
                return re.sub(r"( - Times.*| \| India.*)", "", title)
            return None

        @attribute
        def topics(self) -> List[str]:
            bloat_topics = [
                "India",
                "News",
                "Google News",
                "India Breaking News",
                "India news",
                "Live News India",
                "Top news in India",
            ]
            return [
                topic
                for topic in generic_topic_parsing(self.precomputed.meta.get("news_keywords"))
                if topic not in bloat_topics
            ]
