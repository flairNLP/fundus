from lxml.etree import XPath

from fundus.parser import ParserProxy, function
from fundus.parser.utility import transform_breaks_to_tag
from fundus.publishers.shared.postmedia import PostMediaParser


class FinancialPostParser(ParserProxy):
    class V1(PostMediaParser.V1):
        _paragraph_selector = XPath(
            "//div[@class='story-v2-content-element-inline']/p[not(starts-with(text(), '—')) and (span[text()] or text())]"
        )
        _subheadline_selector = XPath(
            "//div[@class='story-v2-content-element-inline']/*[self::h3 or self::b] |"
            "//div[@class='story-v2-content-element-inline']/p/*[(self::strong or self::b) and not(text())]"
        )

        _bloat_topics = PostMediaParser.V1._bloat_topics | {
            "financialpost.com",
            "wired",
            "Business Wire News Releases",
            "PMN Press Releases",
        }

        @function(priority=0)
        def _replace_br_tags(self):
            transform_breaks_to_tag(self.precomputed.doc)
