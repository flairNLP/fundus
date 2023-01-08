import datetime
import re
from typing import Optional, List, Match

from src.parser.html_parser import BaseParser, register_attribute
from src.parser.html_parser.utility import generic_plaintext_extraction_with_css, generic_author_extraction, \
    generic_date_extraction


class FocusParser(BaseParser):
    _author_substitution_pattern: re.Pattern = re.compile(r'Von FOCUS-online-(Redakteur|Autorin)\s')
    _topic_pattern: re.Pattern = re.compile(r'"keywords":\[{(.*?)}\]')
    _topic_name_pattern: re.Pattern = re.compile(r'"name":"(.*?)"', flags=re.MULTILINE)

    @register_attribute
    def plaintext(self) -> Optional[str]:
        return generic_plaintext_extraction_with_css(self.precomputed.doc,
                                                     "div .leadIn > p, "
                                                     "div .textBlock > p, "
                                                     "div .textBlock > h2")

    @register_attribute
    def authors(self) -> List[str]:
        author_names = generic_author_extraction(self.precomputed.ld, ["author"])
        for i, name in enumerate(author_names):
            author_names[i] = re.sub(self._author_substitution_pattern, '', name)
        return author_names

    @register_attribute
    def publishing_date(self) -> Optional[datetime.datetime]:
        return generic_date_extraction(self.precomputed.ld)

    @register_attribute
    def title(self):
        return self.precomputed.ld.get('headline')

    @register_attribute
    def topics(self) -> List[str]:

        snippet = self.precomputed.doc.xpath(
            'string(//script[@type="text/javascript"][contains(text(), "window.bf__bfa_metadata")])')
        if not snippet:
            return []

        match: Optional[Match] = re.search(self._topic_pattern, snippet)
        if not match:
            return []
        topic_names: List[str] = re.findall(self._topic_name_pattern, match.group(1))

        return topic_names
