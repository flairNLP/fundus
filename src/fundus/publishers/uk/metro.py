import datetime
import re
from typing import List, Optional, Union

from lxml.cssselect import CSSSelector
from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, Image, ParserProxy, attribute
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    generic_topic_parsing,
    image_extraction,
)


class MetroParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime.date(2024, 11, 17)
        _summary_selector = XPath("//article / div[@class='article-body'] / p[1]")
        _subheadline_selector: Union[CSSSelector, XPath] = CSSSelector("article > div.article-body > h2")

        _bloat_regex_ = (
            r"^Got a story|"
            r"^Get in touch with our news team|"
            r"^Get in touch by emailing|"
            r"^If you’ve got a celebrity story|"
            r"^For more stories|"
            r"^Follow Metro|"
            r"^\s*MORE :|"
            r"^Share your views in the comments|"
            r"^Email gamecentral@metro.co.uk|"
            r"^To submit Inbox letters and Reader’s Features more easily|"
            r"^Do you have a story to share?"
        )
        _paragraph_selector = XPath(
            f"//article "
            f"/div[@class='article-body'] "
            f"/p[position()>1 and not(re:test(string(), '{_bloat_regex_}'))]",
            namespaces={"re": "http://exslt.org/regular-expressions"},
        )

        @attribute
        def body(self) -> Optional[ArticleBody]:
            body = extract_article_body_with_selector(
                self.precomputed.doc,
                summary_selector=self._summary_selector,
                subheadline_selector=self._subheadline_selector,
                paragraph_selector=self._paragraph_selector,
            )
            return body

        @attribute
        def publishing_date(self) -> Optional[datetime.datetime]:
            return generic_date_parsing(self.precomputed.ld.bf_search("datePublished"))

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.bf_search("author"))

        @attribute
        def title(self) -> Optional[str]:
            return self.precomputed.ld.bf_search("headline")

        @attribute
        def topics(self) -> List[str]:
            return generic_topic_parsing(self.precomputed.meta.get("article:tag"))

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                upper_boundary_selector=XPath("//article"),
                author_selector=re.compile(r"(?P<credits>\([^(]+\)$)"),
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.date.today()
        _summary_selector = XPath("//article//div[@class='article__content__inner']/p[1]")
        _paragraph_selector = XPath("//article//div[@class='article__content__inner']/p[not(@class) and position()>1]")
        _subheadline_selector = XPath("//article//div[@class='article__content__inner']/h2")
