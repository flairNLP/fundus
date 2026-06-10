from lxml.etree import XPath

from fundus.parser import ParserProxy
from fundus.publishers.ca.national_post import NationalPostParser


class OttawaCitizenParser(ParserProxy):
    class V1(NationalPostParser.V1_1):
        _paragraph_selector = XPath("//div[@class='story-v2-content-element-inline']/p[span[text()] or text()]")
        _subheadline_selector = XPath(
            "//div[@class='story-v2-content-element-inline']/h3 |"
            "//div[@class='story-v2-content-element-inline']/p/*[self::strong or self::b]"
        )

        _bloat_topics = NationalPostParser.V1_1._bloat_topics | {"ottawacitizen.com", "ottawa sun"}
