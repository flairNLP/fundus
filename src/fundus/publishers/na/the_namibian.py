import re
from datetime import datetime
from typing import List, Optional, Pattern
from urllib.parse import urlparse

from lxml.etree import XPath

from fundus.parser import ArticleBody, BaseParser, ParserProxy, attribute, function
from fundus.parser.data import Image
from fundus.parser.utility import (
    extract_article_body_with_selector,
    generic_author_parsing,
    generic_date_parsing,
    load_images_from_html,
    extract_image_data_from_html,
)


class TheNamibianParser(ParserProxy):
    class V1(BaseParser):
        VALID_UNTIL = datetime(year=2024, month=1, day=31).date()
        _summary_selector = XPath("//div[contains(@class, 'tdb-block-inner')]/p[position()=1]")
        _paragraph_selector = XPath("//div[contains(@class, 'tdb-block-inner')]/p[position()>1]")
        _title_substitution_pattern: Pattern[str] = re.compile(r" - The Namibian$")

        @attribute
        def body(self) -> ArticleBody:
            return extract_article_body_with_selector(
                self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                summary_selector=self._summary_selector,
            )

        @attribute
        def publishing_date(self) -> Optional[datetime]:
            return generic_date_parsing(self.precomputed.meta.get("article:published_time"))

        @attribute
        def title(self) -> Optional[str]:
            title = self.precomputed.meta.get("og:title")
            if title is not None:
                return re.sub(self._title_substitution_pattern, "", title)
            return title

        @attribute
        def authors(self) -> List[str]:
            return generic_author_parsing(self.precomputed.ld.get_value_by_key_path(["Person", "name"]))

        @attribute
        def images(self) -> List[Image]:
            publisher_domain = urlparse(self.precomputed.meta.get("og:url")).netloc
            image_list = load_images_from_html(publisher_domain, self.precomputed.doc)
            return extract_image_data_from_html(
                self.precomputed.doc, image_list, self._paragraph_selector, upper_boundary_selector=XPath("//main")
            )

    class V1_1(V1):
        VALID_UNTIL = datetime.today().date()
        _paragraph_selector = XPath("//div[contains(@class, 'entry-content')]/p[position()>1]")
        _summary_selector = XPath("//div[contains(@class, 'entry-content')]/p[position()=1]")
