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
    transform_breaks_to_tag,
)


class TimesOfIndiaParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2026, 3, 28)

        _subheadline_selector = XPath(
            "(//div[@class='_s30J clearfix  '])[1]/div/b |"
            "(//div[@class='_s30J clearfix  '])[1]/div/h2 |"
            "(//div[@class='_s30J clearfix  '])[1]//span[contains(class, strong)]"
        )
        _paragraph_selector = XPath("(//div[@class='_s30J clearfix  '])[1]/p[text()]")
        _summary_selector = XPath("//div[@class='M1rHh undefined']")
        _image_selector: XPath = CSSSelector("section.leadmedia img")

        _image_author_pattern = re.compile(r"\((?P<credits>.*?)\)$")

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
                image_selector=self._image_selector,
                caption_selector=XPath(
                    "./ancestor::section[contains(@class, 'leadmedia')]//div[contains(@class, 'img_cptn')]"
                ),
                author_selector=self._image_author_pattern,
            )

    class V2(BaseParser):
        _paragraph_selector = XPath(
            "(//div[contains(@class,'ihgno')])[1]/p[text()] |(//div[contains(@class,'ihgno')])[1]//li[text()]"
        )
        _subheadline_selector = XPath(
            "(//div[contains(@class,'ihgno')])[1]//*[self::h2 or self::h3 or (span[@class='strong'] and not(text()))]"
        )
        _first_element_pattern = re.compile(
            r"<div class=\"(ihgno|UgCrb) clearfix {2}\">(<div class=\"(e9jwa|XYebw)\"><div class=\"vdo_embedd\">.*? </div></div>)?"
        )

        _image_selector = XPath("//div[contains(@class,'ihgno')]//img")
        _image_author_pattern = re.compile(r"(?i)photo credit:\s*(?P<credits>.*?)$")

        @attribute
        def body(self) -> Optional[ArticleBody]:
            html_as_string = tostring(self.precomputed.doc).decode("utf-8")
            html_as_string = re.sub(
                r"<span class=\"id-r-component br\" data-pos=\"[0-9]*\"></span>", "</p><p>", html_as_string
            )
            html_as_string = re.sub(
                r"<div class=\"cdatainfo[A-z_ ]*id-r-component \" data-pos=\"[0-9]*\">(<h2>[^<]*</h2>)?</div>",
                r"</p>\1<p>",
                html_as_string,
            )
            html_as_string = re.sub(
                self._first_element_pattern, r"<div class=\"ihgno clearfix  \">\2<p>", html_as_string
            )
            html_as_string = re.sub(r"(?i)also read \| <a.*?</a>", "", html_as_string)
            html_as_string = re.sub(
                r"\.<div data-type=\"in_view\" class=\" {2}\">.*?</div></div></div>", ".", html_as_string
            )
            html_as_string = re.sub(r"<p></p>", "", html_as_string)

            return extract_article_body_with_selector(
                fromstring(html_as_string),  # type: ignore
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
        def topics(self) -> List[str]:
            return [
                topic.title()
                for topic in generic_topic_parsing(self.precomputed.meta.get("news_keywords"))
                if "News" not in topic.title()
            ]

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.xpath_search("//NewsArticle/headline", scalar=True)

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=CSSSelector("div.contentwrapper.clearfix"),
                lower_boundary_selector=CSSSelector("div.authorComment"),
                image_selector=self._image_selector,
                caption_selector=XPath(
                    "./ancestor::section[contains(@class, 'leadmedia')]//div[contains(@class, 'img_cptn')]"
                ),
                author_selector=self._image_author_pattern,
            )
