import lxml.html
from lxml.etree import XPath

from fundus.parser.extraction import extract_article_body_with_selector


class TestExtractArticleBodyWithSelector:
    def test_tag_filter_drops_nodes_left_empty(self):
        doc = lxml.html.document_fromstring(
            "<html><body>"
            "<p> <aside><script>advertisement()</script></aside> </p>"
            "<p>First paragraph</p>"
            "<p>Second <aside>Read more</aside>paragraph</p>"
            "</body></html>"
        )

        body = extract_article_body_with_selector(doc, paragraph_selector=XPath("//p"), tag_filter=XPath("self::aside"))

        assert [str(paragraph) for section in body.sections for paragraph in section.paragraphs] == [
            "First paragraph",
            "Second paragraph",
        ]
