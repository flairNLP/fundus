import re
from typing import List

from lxml.etree import XPath

from fundus.parser import Image, ParserProxy, attribute
from fundus.parser.utility import image_extraction
from fundus.publishers.shared.postmedia import PostMediaParser


class CanadaComParser(ParserProxy):
    class V1(PostMediaParser.V1):
        _paragraph_selector = XPath("//section[contains(@class, 'article-content')]//p[text() or span[text()]]")
        _subheadline_selector = XPath(
            "//section[contains(@class, 'article-content')]//*[(self::h3 or self::h2) and not(@class)]"
        )

        _bloat_topics = PostMediaParser.V1._bloat_topics | {
            "o.canada.com",
            "General",
            "Canadians",
        }

        @attribute
        def images(self) -> List[Image]:
            return image_extraction(
                doc=self.precomputed.doc,
                paragraph_selector=self._paragraph_selector,
                caption_selector=XPath("./ancestor::figure/figcaption/span[@class='caption']"),
                author_selector=re.compile(r"\. (?P<credits>.*?[^.])$"),
            )
