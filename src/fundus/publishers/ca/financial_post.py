from lxml.etree import XPath

from fundus.parser import ParserProxy
from fundus.publishers.shared.postmedia import PostMediaParser


class FinancialPostParser(ParserProxy):
    class V1(PostMediaParser.V1):
        _paragraph_selector = XPath(
            "//div[@class='story-v2-content-element-inline']/p[not(starts-with(text(), '—')) and (span[text()] or text())]"
        )
        _subheadline_selector = XPath(
            "//div[@class='story-v2-content-element-inline']/h3 |"
            "//div[@class='story-v2-content-element-inline']/p/*[self::strong or self::b]"
        )

        _bloat_topics = PostMediaParser.V1._bloat_topics | {
            "financialpost.com",
            "wired",
            "Business Wire News Releases",
            "PMN Press Releases",
        }
