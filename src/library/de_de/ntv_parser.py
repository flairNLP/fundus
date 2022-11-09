import datetime
from typing import Optional, List

from dateutil import parser

from src.html_parser import BaseParser
from src.html_parser.base_parser import register_attribute


class NTVParser(BaseParser):
    """
    This parser is for the old format!
    """

    @register_attribute
    def plaintext(self) -> Optional[str]:
        return self.generic_plaintext_extraction_with_css(
            ".article__text > p"
        )

    @register_attribute
    def authors(self) -> List[str]:
        return self.generic_author_extraction(self.meta(), ["author"])

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:

        iso_date_str = self.ld().get('datePublished')
        if iso_date_str:
            return parser.parse(iso_date_str)
        return None

    @register_attribute
    def title(self):
        return self.meta().get('og:title')

    @register_attribute
    def topics(self) -> Optional[str]:
        return self.generic_topic_extraction()
