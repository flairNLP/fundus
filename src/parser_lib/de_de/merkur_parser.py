import datetime
from typing import Optional, List

from dateutil import parser

from src.html_parser import BaseParser
from src.html_parser.base_parser import register_attribute
from src.html_parser.utility import extract_plaintext_from_css_selector


class MerkurParser(BaseParser):
    """
    This parser is for the old format!
    """

    @register_attribute
    def plaintext(self) -> Optional[str]:
        return extract_plaintext_from_css_selector(self.cache['doc'],
                                                   "p.id-StoryElement-leadText ,"
                                                   "p.id-StoryElement-summary ,"
                                                   "p.id-StoryElement-leadText ,"
                                                   "p.id-StoryElement-paragraph"
                                                   )

    @register_attribute
    def authors(self) -> List[str]:
        try:
            raw_str = self.ld().get('mainEntity').get('author')
            # This is a copy from qse and should be done properly
            if isinstance(raw_str, str):
                return [raw_str]

            if isinstance(raw_str, list):
                authors = [author.get('name') for author in raw_str]
            else:
                authors = [raw_str.get('name')]
            return authors
        except KeyError:
            return []
        if raw_str:
            return [raw_str]
        else:
            return []

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        current_ld = self.ld().get('mainEntity')
        if current_ld:
            iso_date_str = current_ld.get('datePublished')
        else:
            return None
        if iso_date_str:
            return parser.parse(iso_date_str)
        return None

    @register_attribute
    def title(self):
        return self.meta().get('og:title')
